function openerp_pos_models(instance, module){ //module is instance.point_of_sale
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
    
    // The PosModel contains the Point Of Sale's representation of the backend.
    // Since the PoS must work in standalone ( Without connection to the server ) 
    // it must contains a representation of the server's PoS backend. 
    // (taxes, product list, configuration options, etc.)  this representation
    // is fetched and stored by the PosModel at the initialisation. 
    // this is done asynchronously, a ready deferred alows the GUI to wait interactively 
    // for the loading to be completed 
    // There is a single instance of the PosModel for each Front-End instance, it is usually called
    // 'pos' and is available to almost all widgets.

    module.PosModel = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            var  self = this;
            this.dao = new module.LocalStorageDAO();            // used to store the order's data on the Hard Drive
            this.ready = $.Deferred();                          // used to notify the GUI that the PosModel has loaded all resources
            this.flush_mutex = new $.Mutex();                   // used to make sure the orders are sent to the server once at time
            this.build_tree = _.bind(this.build_tree, this);    // ???
            this.session = session;                 
            this.categories = {};
            this.barcode_reader = new module.BarcodeReader({'pos': this});  // used to read barcodes
            this.proxy = new module.ProxyDevice();             // used to communicate to the hardware devices via a local proxy

            // default attributes values. If null, it will be loaded below.
            this.set({
                'nbr_pending_operations': 0,    

                'currency':         {symbol: '$', position: 'after'},
                'shop':             null, 
                'company':          null,
                'user':             null,

                'orders':           new module.OrderCollection(),
                'products':         new module.ProductCollection(),
                'cashRegisters':    null, 

                'product_list':     null,
                'bank_statements':  null,
                'taxes':            null,
                'pos_session':      null,
                'pos_config':       null,
                'categories':       null,

                'selectedOrder':    undefined,
            });

            this.get('orders').bind('remove', _.bind( this.on_removed_order, this ) );
            
            // We fetch the backend data on the server asynchronously

            var cat_def = fetch('pos.category', ['name', 'parent_id', 'child_id'])
                .pipe(function(result){
                    return self.set({'categories': result});
                });
            
            var prod_def = fetch( 
                'product.product', 
                ['name', 'list_price', 'pos_categ_id', 'taxes_id','product_image_small', 'ean13'],
                [['pos_categ_id','!=', false]] 
                ).then(function(result){
                    self.set({'product_list': result});
                });


            var tax_def = fetch('account.tax', ['amount','price_include','type'])
                .then(function(result){
                    self.set({'taxes': result});
                });

            var session_def = fetch(    // loading the PoS Session.
                    'pos.session',
                    ['id', 'journal_ids','name','user_id','config_id','start_at','stop_at'],
                    [['state', '=', 'opened'], ['user_id', '=', this.session.uid]]
                ).pipe(function(result) {

                    // some data are associated with the pos session, like the pos config and bank statements.
                    // we must have a valid session before we can read those. 
                    
                    var session_data_def = new $.Deferred();

                    if( result.length !== 0 ) {
                        var pos_session = result[0];

                        self.set({'pos_session': pos_session});

                        var pos_config_def = fetch(
                                'pos.config',
                                ['name','journal_ids','shop_id','journal_id',
                                 'iface_self_checkout', 'iface_websql', 'iface_led', 'iface_cashdrawer',
                                 'iface_payment_terminal', 'iface_electronic_scale', 'iface_barscan', 'iface_vkeyboard',
                                 'iface_print_via_proxy','state','sequence_id','session_ids'],
                                [['id','=', pos_session.config_id[0]]]
                            ).then(function(result){
                                self.set({'pos_config': result[0]});
                            });

                        var bank_def = fetch(
                            'account.bank.statement',
                            ['account_id','currency','journal_id','state','name','user_id'],
                            [['state','=','open'],['user_id', '=', pos_session.user_id[0]]]
                            ).then(function(result){
                                self.set({'bank_statements':result});
                            });
                        

                        var journal_def = fetch(
                            'account.journal',
                            undefined,
                            [['user_id','=',pos_session.user_id[0]]]
                            ).then(function(result){
                                self.set({'journals':result});
                            });

                        // associate the bank statements with their journals. 
                        var bank_process_def = $.when(bank_def, journal_def)
                            .then(function(){
                                var bank_statements = self.get('bank_statements');
                                var journals = self.get('journals');
                                for(var i = 0, ilen = bank_statements.length; i < ilen; i++){
                                    for(var j = 0, jlen = journals.length; j < jlen; j++){
                                        if(bank_statements[i].journal_id[0] === journals[j].id){
                                            bank_statements[i].journal = journals[j];
                                        }
                                    }
                                }
                            });

                        session_data_def = $.when(pos_config_def,bank_def,journal_def,bank_process_def);

                    }else{
                        session_data_def.reject();
                    }
                    return session_data_def;
                });

            // when all the data has loaded, we compute some stuff, and declare the Pos ready to be used. 
            $.when(cat_def, prod_def, session_def, tax_def, this.get_app_data(), this.flush())
                .then(function(){ 
                    self.build_tree();
                    self.set({'cashRegisters' : new module.CashRegisterCollection(self.get('bank_statements'))});
                    console.log('cashRegisters:',self.get('cashRegisters'));
                    self.ready.resolve();
                    self.log_loaded_data();
                });
        },

        // logs the usefull posmodel data to the console for debug purposes
        log_loaded_data: function(){
            console.log('PosModel data has been loaded:');
            console.log('PosModel: categories:',this.get('categories'));
            console.log('PosModel: product_list:',this.get('product_list'));
            console.log('PosModel: bank_statements:',this.get('bank_statements'));
            console.log('PosModel: journals:',this.get('journals'));
            console.log('PosModel: taxes:',this.get('taxes'));
            console.log('PosModel: pos_session:',this.get('pos_session'));
            console.log('PosModel: pos_config:',this.get('pos_config'));
            console.log('PosModel: cashRegisters:',this.get('cashRegisters'));
            console.log('PosModel: shop:',this.get('shop'));
            console.log('PosModel: company:',this.get('company'));
            console.log('PosModel: currency:',this.get('currency'));
            console.log('PosModel.session:',this.session);
            console.log('PosModel.categories:',this.categories);
            console.log('PosModel end of data log.');

        },
        
        // this is called when an order is removed from the order collection. It ensures that there is always an existing
        // order and a valid selected order
        on_removed_order: function(removed_order){
            if( this.get('orders').isEmpty()){
                this.add_and_select_order(new module.Order({ pos: this }));
            }
            if( this.get('selectedOrder') === removed_order){
                this.set({ selectedOrder: this.get('orders').last() });
            }
        },

        // load some data from the server, used in initialize
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
            console.log('push_order',record);
            return this.dao.add_operation(record).pipe(function(){
                    return self.flush();
            });
        },

        add_and_select_order: function(newOrder) {
            (this.get('orders')).add(newOrder);
            return this.set({
                selectedOrder: newOrder
            });
        },
        
        // attemps to send all pending orders ( stored in the DAO ) to the server.
        // it will do it one by one, and remove the successfully sent ones from the DAO once
        // it has been confirmed that they have been received.
        flush: function() {
            //this makes sure only one _int_flush is called at the same time
            console.log('flush operations');
            return this.flush_mutex.exec(_.bind(function() {
                return this._int_flush();
            }, this));
        },
        _int_flush : function() {
            var self = this;

            this.dao.get_operations().pipe(function(operations) {
                // operations are really Orders that are converted to json.
                // they are saved to disk and then we attempt to send them to the backend so that they can
                // be applied. 
                // since the network is not reliable we potentially have many 'pending operations' that have not been sent.

                self.set( {'nbr_pending_operations':operations.length} );
                if(operations.length === 0){
                    return $.when();
                }
                var op = operations[0];

                 // we prevent the default error handler and assume errors
                 // are a normal use case, except we stop the current iteration

                 return (new instance.web.Model('pos.order')).get_func('create_from_ui')([op])
                            .fail(function(unused, event){
                                // wtf ask niv
                                event.preventDefault();
                            })
                            .pipe(function(){
                                // success: remove the successfully sent operation, and try to send the next one 
                                self.dao.remove_operation(operations[0].id).pipe(function(){
                                    return self._int_flush();
                                });
                            }, function(){
                                // in case of error we just sit there and do nothing. wtf ask niv
                                return $.when();
                            });
            });
        },
        // I guess this builds a tree of categories ? TODO ask Niv for more info.
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

    // An orderline represent one element of the content of a client's shopping cart.
    // An orderline contains a product, its quantity, its price, discount. etc. 
    // Currently there is a limitation in that there can only be once orderline by type
    // of product, but this will be subject to changes TODO
    //
    // An Order contains zero or more Orderlines.
    module.Orderline = Backbone.Model.extend({
        defaults: {
            quantity: 1,
            list_price: 0,
            discount: 0,
            weighted: false,
            product_type: 'unit',
        },
        initialize: function(attributes) {
            this.pos = attributes.pos;
            Backbone.Model.prototype.initialize.apply(this, arguments);

            if(attributes.weight){
                this.setWeight(attributes.weight);
                this.set({weighted: true});
                this.set({product_type: 'weight'});
            }

            this.bind('change:quantity', function(unused, qty) {
                if (qty == 0)
                    this.trigger('killme');
            }, this);
        },

        // when we add an new orderline we want to merge it with the last line to see reduce the number of items
        // in the orderline. This returns true if it makes sense to merge the two
        can_be_merged_with: function(orderline){
            if( this.get('id') !== orderline.get('id')){    //only orderline of the same product can be merged
                return false;
            }else if(this.get('product_type') !== orderline.get('product_type')){
                return false;
            }else if(this.get('discount') > 0){             // we don't merge discounted orderlines
                return false;
            }else if(this.get('product_type') === 'unit'){ 
                return true;
            }else if(this.get('product_type') === 'weight'){
                return true;
            }else if(this.get('product_type') === 'price'){
                return this.get('list_price') === orderline.get('list_price');
            }else{
                console.error('point_of_sale/pos_models.js/Orderline.can_be_merged_with() : unknown product type:',this.get('product_type'));
                return false;
            }
        },

        // Modifies this orderline so that it also contains the contents of another orderline.
        // the two orderlines must be mergable ('can_be_merged_with()' === true) 
        merge: function(orderline){
            this.set({quantity : this.get('quantity') + orderline.get('quantity') });
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
        set_discount: function(discount){
            this.set({'discount': discount});
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
    
    // An order more or less represents the content of a client's shopping cart (the OrderLines) 
    // plus the associated payment information (the PaymentLines) 
    // there is always an active ('selected') order in the Pos, a new one is created
    // automaticaly once an order is completed and sent to the server.

    module.Order = Backbone.Model.extend({
        initialize: function(attributes){
            Backbone.Model.prototype.initialize.apply(this, arguments);
            this.set({
                creationDate:   new Date(),
                orderLines:     new module.OrderlineCollection(),
                paymentLines:   new module.PaymentlineCollection(),
                name:           "Order " + this.generateUniqueId(),
            });
            this.pos =     attributes.pos; //TODO put that in set and remember to use 'get' to read it ... 
            this.pos_widget = attributes.pos_widget;    //FIXME we shouldn't depend on pos_widget in the models
            this.last_orderline = undefined;
            return this;
        },
        generateUniqueId: function() {
            return new Date().getTime();
        },
        addProduct: function(product){
            var attr = product.toJSON();
            attr.pos = this.pos;
            var line = new module.Orderline(attr);
            var self = this;

            if( this.last_orderline && this.last_orderline.can_be_merged_with(line) ){
                this.last_orderline.merge(line);
            }else{
                this.get('orderLines').add(line);
                line.bind('killme', function() { 
                    this.get('orderLines').remove(line);
                }, this);
                this.last_orderline = line;
            }
        },
        addProductOld: function(product) {
            var existing;

            existing = (this.get('orderLines')).get(product.id);
            if (existing != null) {
                this.last_orderline = existing;
                if(existing.get('weighted')){
                    existing.incrementWeight(product.attributes.weight);
                }else{
                    existing.incrementQuantity();
                }
            } else {
                var attr = product.toJSON();
                attr.pos = this.pos;
                var line = new module.Orderline(attr);
                console.log('new Orderline:',line,attr);
                this.last_orderline = line;
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
            	this.trigger('set_value', parseFloat(bufferContent));
            }
        },
    });
}
