function pos_models(module, instance){
    var QWeb = instance.web.qweb;

    module.LocalStorageDAO = instance.web.Class.extend({
        add_operation: function(operation) {
            var self = this;
            return $.async_when().pipe(function() {
                var tmp = self._get('oe_pos_operations', []);
                var last_id = self._get('oe_pos_operations_sequence', 1);
                tmp.push({'id': last_id, 'data': operation});
                self._set('oe_pos_operations', tmp);
                self._set('oe_pos_operations_sequence', last_id + 1);
            });
        },
        remove_operation: function(id) {
            var self = this;
            return $.async_when().pipe(function() {
                var tmp = self._get('oe_pos_operations', []);
                tmp = _.filter(tmp, function(el) {
                    return el.id !== id;
                });
                self._set('oe_pos_operations', tmp);
            });
        },
        get_operations: function() {
            var self = this;
            return $.async_when().pipe(function() {
                return self._get('oe_pos_operations', []);
            });
        },
        _get: function(key, default_) {
            var txt = localStorage[key];
            if (! txt)
                return default_;
            return JSON.parse(txt);
        },
        _set: function(key, value) {
            localStorage[key] = JSON.stringify(value);
        },
    });

    var fetch = function(osvModel, fields, domain){
        var dataSetSearch = new instance.web.DataSetSearch(null, osvModel, {}, domain);
        return dataSetSearch.read_slice(fields, 0);
    };
    
    /*
     Gets all the necessary data from the OpenERP web client (instance, shop data etc.)
     */
    module.PosModel = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            var  self = this;
            this.dao = new module.LocalStorageDAO();
            this.ready = $.Deferred();
            this.flush_mutex = new $.Mutex();
            this.build_tree = _.bind(this.build_tree, this);
            this.session = session;
            this.categories = {};
            this.set({
                'nbr_pending_operations': 0,
                'currency': {symbol: '$', position: 'after'},
                'shop': {},
                'company': {},
                'user': {},
                'orders': new module.OrderCollection(),
                'products': new module.ProductCollection(),
                //'cashRegisters': [], // new module.CashRegisterCollection(this.pos.get('bank_statements')),
                'selectedOrder': undefined,
            });
            
            var cat_def = fetch('pos.category', ['name', 'parent_id', 'child_id'])
                .pipe(function(result){
                    return self.set({'categories': result});
                });
            
            var prod_def = fetch( 
                'product.product', 
                ['name', 'list_price', 'pos_categ_id', 'taxes_id','product_image_small'],
                [['pos_categ_id','!=', 'false']] 
                ).then(function(result){
                    return self.set({'product_list': result});
                });

            var bank_def = fetch(
                'account.bank.statement', 
                ['account_id', 'currency', 'journal_id', 'state', 'name'],
                [['state','=','open'], ['user_id', '=', this.session.uid]]
                ).then(function(result){
                    return self.set({'bank_statements': result});
                });

            var tax_def = fetch('account.tax', ['amount','price_include','type'])
                .then(function(result){
                    return self.set({'taxes': result});
                });

            $.when(cat_def,prod_def,bank_def,tax_def,this.get_app_data(), this.flush())
                .pipe(_.bind(this.build_tree, this))
                .pipe(function(){
                    self.set({'cashRegisters': new module.CashRegisterCollection(self.get('bank_statements')) });
                    self.ready.resolve();
                });

            return (this.get('orders')).bind('remove', _.bind( function(removedOrder) {
                if ((this.get('orders')).isEmpty()) {
                    this.addAndSelectOrder(new module.Order({pos: self}));
                }
                if ((this.get('selectedOrder')) === removedOrder) {
                    return this.set({
                        selectedOrder: (this.get('orders')).last()
                    });
                }
            }, this));

        },

        get_app_data: function() {
            var self = this;
            return $.when(new instance.web.Model("sale.shop").get_func("search_read")([]).pipe(function(result) {
                self.set({'shop': result[0]});
                var company_id = result[0]['company_id'][0];
                return new instance.web.Model("res.company").get_func("read")(company_id, ['currency_id', 'name', 'phone']).pipe(function(result) {
                    self.set({'company': result});
                    var currency_id = result['currency_id'][0]
                    return new instance.web.Model("res.currency").get_func("read")([currency_id],
                            ['symbol', 'position']).pipe(function(result) {
                        self.set({'currency': result[0]});
                        
                    });
                });
            }), new instance.web.Model("res.users").get_func("read")(this.session.uid, ['name']).pipe(function(result) {
                self.set({'user': result});
            }));
        },
        push_order: function(record) {
            var self = this;
            return this.dao.add_operation(record).pipe(function(){
                    return self.flush();
            });
        },
        addAndSelectOrder: function(newOrder) {
            (this.get('orders')).add(newOrder);
            return this.set({
                selectedOrder: newOrder
            });
        },
        flush: function() {
            return this.flush_mutex.exec(_.bind(function() {
                return this._int_flush();
            }, this));
        },
        _int_flush : function() {
            var self = this;
            
            this.dao.get_operations().pipe(function(operations) {
                self.set( {'nbr_pending_operations':operations.length} );
                if(operations.length === 0){
                    return $.when();
                }
                var op = operations[0].data;

                 // we prevent the default error handler and assume errors
                 // are a normal use case, except we stop the current iteration

                 return new instance.web.Model('pos.order').get_func('create_from_ui')([op])
                            .fail(function(unused, event){
                                event.preventDefault();
                            })
                            .pipe(function(){
                                //console.debug('saved 1 record'); TODO Debug this
                                self.dao.remove_operation(op.id).pipe(function(){
                                    return self._int_flush();
                                });
                            }, function(){
                                return $.when();
                            });
            });
        },
        build_tree: function() {
            var c, id, _i, _len, _ref, _ref2;
            _ref = this.get('categories');
            for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                c = _ref[_i];
                this.categories[c.id] = {
                    id: c.id,
                    name: c.name,
                    children: c.child_id,
                    parent: c.parent_id[0],
                    ancestors: [c.id],
                    subtree: [c.id]
                };
            }
            _ref2 = this.categories;
            for (id in _ref2) {
                c = _ref2[id];
                this.current_category = c;
                this.build_ancestors(c.parent);
                this.build_subtree(c);
            }
            this.categories[0] = {
                ancestors: [],
                children: (function() {
                    var _j, _len2, _ref3, _results;
                    _ref3 = this.get('categories');
                    _results = [];
                    for (_j = 0, _len2 = _ref3.length; _j < _len2; _j++) {
                        c = _ref3[_j];
                        if (!(c.parent_id[0] != null)) {
                            _results.push(c.id);
                        }
                    }
                    return _results;
                }).call(this),
                subtree: (function() {
                    var _j, _len2, _ref3, _results;
                    _ref3 = this.get('categories');
                    _results = [];
                    for (_j = 0, _len2 = _ref3.length; _j < _len2; _j++) {
                        c = _ref3[_j];
                        _results.push(c.id);
                    }
                    return _results;
                }).call(this)
            };
        },
        build_ancestors: function(parent) {
            if (parent != null) {
                this.current_category.ancestors.unshift(parent);
                return this.build_ancestors(this.categories[parent].parent);
            }
        },
        build_subtree: function(category) {
            var c, _i, _len, _ref, _results;
            _ref = category.children;
            _results = [];
            for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                c = _ref[_i];
                this.current_category.subtree.push(c);
                _results.push(this.build_subtree(this.categories[c]));
            }
            return _results;
        }
    });
    /*
    module.Shop = Backbone.Model.extend({
        initialize: function(attributes) {
            var self = this;
            this.set({
                orders: new module.OrderCollection(),
                products: new module.ProductCollection(),
            });
            this.pos = attributes.pos;
            this.set({
                cashRegisters: new module.CashRegisterCollection(this.pos.get('bank_statements')),
            });
            return (this.get('orders')).bind('remove', _.bind( function(removedOrder) {
                if ((this.get('orders')).isEmpty()) {
                    this.addAndSelectOrder(new module.Order({pos: self.pos}));
                }
                if ((this.get('selectedOrder')) === removedOrder) {
                    return this.set({
                        selectedOrder: (this.get('orders')).last()
                    });
                }
            }, this));
        },
        addAndSelectOrder: function(newOrder) {
            (this.get('orders')).add(newOrder);
            return this.set({
                selectedOrder: newOrder
            });
        },
    });*/

    module.CashRegister = Backbone.Model.extend({
    });

    module.CashRegisterCollection = Backbone.Collection.extend({
        model: module.CashRegister,
    });

    module.Product = Backbone.Model.extend({
    });

    module.ProductCollection = Backbone.Collection.extend({
        model: module.Product,
    });

    /*
     Each Order contains zero or more Orderlines (i.e. the content of the "shopping cart".)
     There should only ever be one Orderline per distinct product in an Order.
     To add more of the same product, just update the quantity accordingly.
     The Order also contains payment information.
     */
    module.Orderline = Backbone.Model.extend({
        defaults: {
            quantity: 1,
            list_price: 0,
            discount: 0
        },
        initialize: function(attributes) {
            this.pos = attributes.pos;
            Backbone.Model.prototype.initialize.apply(this, arguments);
            this.bind('change:quantity', function(unused, qty) {
                if (qty == 0)
                    this.trigger('killme');
            }, this);
        },
        incrementQuantity: function() {
            return this.set({
                quantity: (this.get('quantity')) + 1
            });
        },
        getPriceWithoutTax: function() {
            return this.getAllPrices().priceWithoutTax;
        },
        getPriceWithTax: function() {
            return this.getAllPrices().priceWithTax;
        },
        getTax: function() {
            return this.getAllPrices().tax;
        },
        getAllPrices: function() {
            var self = this;
            var base = (this.get('quantity')) * (this.get('list_price')) * (1 - (this.get('discount')) / 100);
            var totalTax = base;
            var totalNoTax = base;
            
            var product_list = self.pos.get('product_list');
            var product = _.detect(product_list, function(el) {return el.id === self.get('id');});
            var taxes_ids = product.taxes_id;
            var taxes =  self.pos.get('taxes');
            var taxtotal = 0;
            _.each(taxes_ids, function(el) {
                var tax = _.detect(taxes, function(t) {return t.id === el;});
                if (tax.price_include) {
                    var tmp;
                    if (tax.type === "percent") {
                        tmp =  base - (base / (1 + tax.amount));
                    } else if (tax.type === "fixed") {
                        tmp = tax.amount * self.get('quantity');
                    } else {
                        throw "This type of tax is not supported by the point of sale: " + tax.type;
                    }
                    taxtotal += tmp;
                    totalNoTax -= tmp;
                } else {
                    var tmp;
                    if (tax.type === "percent") {
                        tmp = tax.amount * base;
                    } else if (tax.type === "fixed") {
                        tmp = tax.amount * self.get('quantity');
                    } else {
                        throw "This type of tax is not supported by the point of sale: " + tax.type;
                    }
                    taxtotal += tmp;
                    totalTax += tmp;
                }
            });
            return {
                "priceWithTax": totalTax,
                "priceWithoutTax": totalNoTax,
                "tax": taxtotal,
            };
        },
        exportAsJSON: function() {
            return {
                qty: this.get('quantity'),
                price_unit: this.get('list_price'),
                discount: this.get('discount'),
                product_id: this.get('id')
            };
        },
    });

    module.OrderlineCollection = Backbone.Collection.extend({
        model: module.Orderline,
    });

    // Every PaymentLine has all the attributes of the corresponding CashRegister.
    module.Paymentline = Backbone.Model.extend({
        defaults: { 
            amount: 0,
        },
        initialize: function(attributes) {
            Backbone.Model.prototype.initialize.apply(this, arguments);
        },
        getAmount: function(){
            return this.get('amount');
        },
        exportAsJSON: function(){
            return {
                name: instance.web.datetime_to_str(new Date()),
                statement_id: this.get('id'),
                account_id: (this.get('account_id'))[0],
                journal_id: (this.get('journal_id'))[0],
                amount: this.getAmount()
            };
        },
    });

    module.PaymentlineCollection = Backbone.Collection.extend({
        model: module.Paymentline,
    });
    
    module.Order = Backbone.Model.extend({
        defaults:{
            validated: false,
            step: 'products',
        },
        initialize: function(attributes){
            Backbone.Model.prototype.initialize.apply(this, arguments);
            this.set({
                creationDate:   new Date(),
                orderLines:     new module.OrderlineCollection(),
                paymentLines:   new module.PaymentlineCollection(),
                name:           "Order " + this.generateUniqueId(),
            });
            this.pos =     attributes.pos; //TODO put that in set and remember to use 'get' to read it ... 
            this.bind('change:validated', this.validatedChanged);
            return this;
        },
        events: {
            'change:validated': 'validatedChanged'
        },
        validatedChanged: function() {
            if (this.get("validated") && !this.previous("validated")) {
                this.set({'step': 'receipt'});
            }
        },
        generateUniqueId: function() {
            return new Date().getTime();
        },
        addProduct: function(product) {
            var existing;
            existing = (this.get('orderLines')).get(product.id);
            if (existing != null) {
                existing.incrementQuantity();
            } else {
                var attr = product.toJSON();
                attr.pos = this.pos;
                var line = new module.Orderline(attr);
                this.get('orderLines').add(line);
                line.bind('killme', function() {
                    this.get('orderLines').remove(line);
                }, this);
            }
        },
        addPaymentLine: function(cashRegister) {
            var newPaymentline;
            newPaymentline = new module.Paymentline(cashRegister);
            /* TODO: Should be 0 for cash-like accounts */
            newPaymentline.set({
                amount: this.getDueLeft()
            });
            return (this.get('paymentLines')).add(newPaymentline);
        },
        getName: function() {
            return this.get('name');
        },
        getTotal: function() {
            return (this.get('orderLines')).reduce((function(sum, orderLine) {
                return sum + orderLine.getPriceWithTax();
            }), 0);
        },
        getTotalTaxExcluded: function() {
            return (this.get('orderLines')).reduce((function(sum, orderLine) {
                return sum + orderLine.getPriceWithoutTax();
            }), 0);
        },
        getTax: function() {
            return (this.get('orderLines')).reduce((function(sum, orderLine) {
                return sum + orderLine.getTax();
            }), 0);
        },
        getPaidTotal: function() {
            return (this.get('paymentLines')).reduce((function(sum, paymentLine) {
                return sum + paymentLine.getAmount();
            }), 0);
        },
        getChange: function() {
            return this.getPaidTotal() - this.getTotal();
        },
        getDueLeft: function() {
            return this.getTotal() - this.getPaidTotal();
        },
        exportAsJSON: function() {
            var orderLines, paymentLines;
            orderLines = [];
            (this.get('orderLines')).each(_.bind( function(item) {
                return orderLines.push([0, 0, item.exportAsJSON()]);
            }, this));
            paymentLines = [];
            (this.get('paymentLines')).each(_.bind( function(item) {
                return paymentLines.push([0, 0, item.exportAsJSON()]);
            }, this));
            return {
                name: this.getName(),
                amount_paid: this.getPaidTotal(),
                amount_total: this.getTotal(),
                amount_tax: this.getTax(),
                amount_return: this.getChange(),
                lines: orderLines,
                statement_ids: paymentLines
            };
        },
    });

    module.OrderCollection = Backbone.Collection.extend({
        model: module.Order,
    });


    /*
     The numpad handles both the choice of the property currently being modified
     (quantity, price or discount) and the edition of the corresponding numeric value.
     */
    module.NumpadState = Backbone.Model.extend({
        defaults: {
            buffer: "0",
            mode: "quantity"
        },
        appendNewChar: function(newChar) {
            var oldBuffer;
            oldBuffer = this.get('buffer');
            if (oldBuffer === '0') {
                this.set({
                    buffer: newChar
                });
            } else if (oldBuffer === '-0') {
                this.set({
                    buffer: "-" + newChar
                });
            } else {
                this.set({
                    buffer: (this.get('buffer')) + newChar
                });
            }
            this.updateTarget();
        },
        deleteLastChar: function() {
            var tempNewBuffer;
            tempNewBuffer = (this.get('buffer')).slice(0, -1) || "0";
            if (isNaN(tempNewBuffer)) {
                tempNewBuffer = "0";
            }
            this.set({
                buffer: tempNewBuffer
            });
            this.updateTarget();
        },
        switchSign: function() {
            var oldBuffer;
            oldBuffer = this.get('buffer');
            this.set({
                buffer: oldBuffer[0] === '-' ? oldBuffer.substr(1) : "-" + oldBuffer
            });
            this.updateTarget();
        },
        changeMode: function(newMode) {
            this.set({
                buffer: "0",
                mode: newMode
            });
        },
        reset: function() {
            this.set({
                buffer: "0",
                mode: "quantity"
            });
        },
        updateTarget: function() {
            var bufferContent, params;
            bufferContent = this.get('buffer');
            if (bufferContent && !isNaN(bufferContent)) {
            	this.trigger('setValue', parseFloat(bufferContent));
            }
        },
    });

    module.App = (function() {

        function App($element, pos) {
            this.initialize($element, pos);
        }

        App.prototype.initialize = function($element, pos) {
            this.pos = pos;
            this.shopView = new module.ShopWidget(null, {
                'pos': pos,
            });
            this.shopView.$element = $element;
            this.shopView.start();
            this.categoryView = new module.CategoryWidget(null, {element_id: 'products-screen-categories', pos: pos} );
            this.categoryView.on_change_category.add_last(_.bind(this.category, this));
            this.category();

            this.onscreenKeyboard = new module.OnscreenKeyboardWidget(null,{keyboard_model:'simple'});
            this.onscreenKeyboard.appendTo($(".point-of-sale #content"));

            this.actionBar = new module.ActionbarWidget(null);
            this.actionBar.appendTo($(".point-of-sale #content"));

            this.actionBar.addNewButton('left',{
                label : 'Aide',
                icon  : '/point_of_sale/static/src/img/icons/png48/help-browser.png',
            });
            this.actionBar.addNewButton('left',{'label':'test'});
            this.actionBar.addNewButton('left',{'label':'kikoo', rightalign:true});

            this.actionBar.addNewButton('right',{'label':'boo'});
            this.actionBar.addNewButton('right',{
                label      : 'Payer', 
                rightalign : true,
                icon       : '/point_of_sale/static/src/img/icons/png48/go-next.png',
            });
            this.actionBar.addNewButton('right',{
                label      : 'Ook Ook', 
                rightalign : true,
                icon       : '/point_of_sale/static/src/img/icons/png48/face-monkey.png',
            });
        };

        //returns true if the code is a valid EAN codebar number by checking the control digit.
        App.checkEan = function(code){
            var st1 = code.slice();
            var st2 = st1.slice(0,st1.length-1).reverse();
            // some EAN13 barcodes have a length of 12, as they start by 0
            while (st2.length < 12) {
                st2.push(0);
            }
            var countSt3 = 1;
            var st3 = 0;
            $.each(st2, function() {
                if (countSt3%2 === 1) {
                    st3 +=  this;
                }
                countSt3 ++;
            });
            st3 *= 3;
            var st4 = 0;
            var countSt4 = 1;
            $.each(st2, function() {
                if (countSt4%2 === 0) {
                    st4 += this;
                }
                countSt4 ++;
            });
            var st5 = st3 + st4;
            var cd = (10 - (st5%10)) % 10;
            return code[code.length-1] === cd;
        };

        // returns a product that has a packaging with an EAN matching to provided ean string. 
        // returns undefined if no such product is found.
        App.getProductByEAN = function(ean, allPackages, allProducts) {
            var prefix = ean.substring(0,2);
            var scannedProductModel = undefined;

            if (prefix in {'02':'', '22':'', '24':'', '26':'', '28':''}) {
            
                // PRICE barcode
                var itemCode = ean.substring(0,7);
                var scannedPackaging = _.detect(allPackages, function(pack) { return pack.ean !== undefined && pack.ean.substring(0,7) === itemCode;});
                if (scannedPackaging !== undefined) {
                    scannedProductModel = _.detect(allProducts, function(pc) { return pc.id === scannedPackaging.product_id[0];});
                    scannedProductModel.list_price = Number(ean.substring(7,12))/100;
                }
            } else if (prefix in {'21':'','23':'','27':'','29':'','25':''}) {
                // WEIGHT barcode
                var weight = Number(barcode.substring(7,12))/1000;
                var itemCode = ean.substring(0,7);
                var scannedPackaging = _.detect(allPackages, function(pack) { return pack.ean !== undefined && pack.ean.substring(0,7) === itemCode;});
                if (scannedPackaging !== undefined) {
                    scannedProductModel = _.detect(allProducts, function(pc) { return pc.id === scannedPackaging.product_id[0];});
                    scannedProductModel.list_price *= weight;
                    scannedProductModel.name += ' - ' + weight + ' Kg.';
                }
            } else {
                // UNIT barcode
                scannedProductModel = _.detect(allProducts, function(pc) { return pc.ean13 === ean;});   //TODO DOES NOT SCALE
            }
            return scannedProductModel;
        };

        App.prototype.category = function(id) {
            var c, product_list, self = this;

            id = !id ? 0 : id; 

            c = this.pos.categories[id];
            this.categoryView.ancestors = c.ancestors;
            this.categoryView.children = c.children;
            this.categoryView.renderElement();
            this.categoryView.start();

            allProducts = this.pos.get('product_list');

            allPackages = this.pos.get('product.packaging');
            
            product_list = this.pos.get('product_list').filter( function(p) {
                var _ref;
                return _ref = p.pos_categ_id[0], _.indexOf(c.subtree, _ref) >= 0;
            });
            (this.pos.get('products')).reset(product_list);

            var codeNumbers = [];

            // The barcode readers acts as a keyboard, we catch all keyup events and try to find a 
            // barcode sequence in the typed keys, then act accordingly.
            $('body').delegate('','keyup', function (e){

                //We only care about numbers
                if (!isNaN(Number(String.fromCharCode(e.keyCode)))) {

                    // The barcode reader sends keystrokes with a specific interval.
                    // We look if the typed keys fit in the interval. 
                    if (codeNumbers.length==0) {
                        timeStamp = new Date().getTime();
                    } else {
                        if (lastTimeStamp + 30 < new Date().getTime()) {
                            // not a barcode reader
                            codeNumbers = [];
                            timeStamp = new Date().getTime();
                        }
                    }
                    codeNumbers.push(e.keyCode - 48);
                    lastTimeStamp = new Date().getTime();
                    if (codeNumbers.length == 13) {
                        console.log('found code:', codeNumbers.join(''));

                        // a barcode reader
                        if (!App.checkEan(codeNumbers)) {
                            // barcode read error, raise warning
                            $(QWeb.render('pos-scan-warning')).dialog({
                                resizable: false,
                                height:220,
                                modal: true,
                                title: "Warning",
                            });
                        }
                        var selectedOrder = self.pos.get('selectedOrder');
                        var scannedProductModel = App.getProductByEAN(codeNumbers.join(''),allPackages,allProducts);
                        if (scannedProductModel === undefined) {
                            // product not recognized, raise warning
                            $(QWeb.render('pos-scan-warning')).dialog({
                                resizable: false,
                                height:220,
                                modal: true,
                                title: "Warning",
                                /*
                                buttons: {
                                    "OK": function() {
                                        $( this ).dialog( "close" );
                                        return;
                                    },
                                }*/
                            });
                        } else {
                            selectedOrder.addProduct(new module.Product(scannedProductModel));
                        }

                        codeNumbers = [];
                    }
                } else {
                    // NaN
                    codeNumbers = [];
                }
            });

            $('.searchbox input').keyup(function() {
                var m, s;
                s = $(this).val().toLowerCase();
                if (s) {
                    m = product_list.filter( function(p) {
                        return p.name.toLowerCase().indexOf(s) != -1;
                    });
                    $('.search-clear').fadeIn();
                } else {
                    m = product_list;
                    $('.search-clear').fadeOut();
                }
                return (self.pos.get('products')).reset(m);
            });
            return $('.search-clear').click( function() {
                (self.pos.get('products')).reset(product_list);
                $('.searchbox input').val('').focus();
                return $('.search-clear').fadeOut();
            });
        };
        return App;
    })();

}
