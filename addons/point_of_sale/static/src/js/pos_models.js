function openerp_pos_models(module, instance){ //module is instance.point_of_sale
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
            this.barcode_reader = new module.BarcodeReader({'pos': this});
            this.proxy = new module.ProxyDevice({'pos': this});
            this.set({
                'nbr_pending_operations': 0,
                'currency': {symbol: '$', position: 'after'},
                'shop': {},
                'company': {},
                'user': {},
                'orders': new module.OrderCollection(),
                'products': new module.ProductCollection(),
                'selectedOrder': undefined,
            });
            
            var cat_def = fetch('pos.category', ['name', 'parent_id', 'child_id'])
                .pipe(function(result){
                    return self.set({'categories': result});
                });
            
            var prod_def = fetch( 
                'product.product', 
                ['name', 'list_price', 'pos_categ_id', 'taxes_id','product_image_small', 'ean13'],
                [['pos_categ_id','!=', false]] 
                ).then(function(result){
                    console.log('product_list:',result);
                    return self.set({'product_list': result});
                });

            var session_def = fetch(
                    'pos.session',
                    ['id', 'journal_ids'],
                    [['state', '=', 'opened'], ['user_id', '=', this.session.uid]]
                ).then(function(result) {
                    if( result.length !== 0 ) {
                        console.log('pos_session:', result);
                        var journal_def = fetch(
                            'account.journal',
                            ['name'], 
                            [['id', 'in', result[0]['journal_ids']]]).then(function(inner_result) {
                                self.set({'account_journals' : inner_result});
                        });
                    }
                    return self; 
                });

            var tax_def = fetch('account.tax', ['amount','price_include','type'])
                .then(function(result){
                    console.log('taxes:',result);
                    return self.set({'taxes': result});
                });

            $.when(cat_def, prod_def, session_def, tax_def, this.get_app_data(), this.flush())
                .pipe(_.bind(this.build_tree, this))
                .pipe(function(){
                    self.set({'accountJournals' : new module.AccountJournalCollection(self.get('account_journals'))});
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
                var op = operations[0];

                 // we prevent the default error handler and assume errors
                 // are a normal use case, except we stop the current iteration

                 return new instance.web.Model('pos.order').get_func('create_from_ui')([op])
                            .fail(function(unused, event){
                                event.preventDefault();
                            })
                            .pipe(function(){
                                console.debug('saved 1 record'); //TODO Debug this
                                self.dao.remove_operation(operations[0].id).pipe(function(){
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

    module.AccountJournal = Backbone.Model.extend({
    });

    module.AccountJournalCollection = Backbone.Collection.extend({
        model: module.AccountJournal,
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
            discount: 0,
            weighted: false,
        },
        initialize: function(attributes) {
            this.pos = attributes.pos;
            Backbone.Model.prototype.initialize.apply(this, arguments);

            if(attributes.weight){
                this.setWeight(attributes.weight);
                this.set({weighted: true});
            }

            this.bind('change:quantity', function(unused, qty) {
                if (qty == 0)
                    this.trigger('killme');
            }, this);
        },
        setWeight: function(weight){
            return this.set({
                quantity: weight,
            });
        },
        incrementQuantity: function() {
            return this.set({
                quantity: (this.get('quantity')) + 1
            });
        },
        incrementWeight: function(weight){
            return this.set({
                quantity: (this.get('quantity')) + weight,
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
            // FIXME
            return 0.0; //this.get('amount');
        },
        exportAsJSON: function(){
            // FIXME
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
                this.pos.screen_selector.set_current_screen('receipt'); 
                //this.set({'screen': 'receipt'});
            }
        },
        generateUniqueId: function() {
            return new Date().getTime();
        },
        addProduct: function(product) {
            var existing;
            existing = (this.get('orderLines')).get(product.id);
            if (existing != null) {
                if(existing.get('weighted')){
                    existing.incrementWeight(product.attributes.weight);
                }else{
                    existing.incrementQuantity();
                }
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
        addPaymentLine: function(accountJournal) {
            var newPaymentline;
            newPaymentline = new module.Paymentline(accountJournal);
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
}
