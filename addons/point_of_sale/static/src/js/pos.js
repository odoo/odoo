(function(){
    window.asyncStorageDelay = 0;
    window.asyncStorage = {
        length: function(){
            var d = $.Deferred();
            setTimeout(function(){
                d.resolve(localStorage.length);
            },asyncStorageDelay);
            return d.promise();
        },
        key: function(index){
            var d = $.Deferred();
            setTimeout(function(){
                d.resolve(localStorage.key(index));
            },asyncStorageDelay);
            return d.promise();
        },
        getItem: function(key){
            var d = $.Deferred();
            setTimeout(function(){
                var val = localStorage.getItem(key);
                if(val){
                    d.resolve(val);
                }else{
                    d.reject();
                }
            },asyncStorageDelay);
            return d.promise();
        },
        setItem: function(key,data){
            var d = $.Deferred();
            setTimeout(function(){
                localStorage.setItem(key,data);
                d.resolve();
            },asyncStorageDelay);
            return d.promise();
        },
        removeItem: function(key){
            var d = $.Deferred();
            setTimeout(function(){
                localStorage.removeItem(key);
                d.resolve();
            },asyncStorageDelay);
            return d.promise();
        },
        clear: function(){
            var d = $.Deferred();
            setTimeout(function(){
                localStorage.clear();
                d.resolve();
            },asyncStorageDelay);
            return d.promise();
        },
        
        // A collection holds  a list of objects that can be stored and searched on the disc asynchronously.
        // collection : the name of the collection.
        // searchable_fields : a list of the name of the object's field that can be searched and matched
        collection_new: function(collection, searchable_fields){
            var col_obj = {
                    'name': collection,
                    'searchable_fields': searchable_fields || [],
                    'data': [],
            };
            return asyncStorage.setItem('collection_'+collection, JSON.stringify(col_obj));
        },
        
        // returns a defered that fetches one element of the collection that has a field of value equal to name
        // the defered fails if there is no such element
        collection_get: function(collection, field, name){
            var d = $.Deferred();

            setTimeout(function(){
                var col_str = localStorage.getItem('collection_'+collection)
                var col_obj = JSON.parse(col_str);
                var data = col_obj.data;
                for(var i = 0; i < data.length; i++){
                    var elem = data[i];
                    if (elem[field] && elem[field] === name){
                        d.resolve(elem);
                        return d.promise();
                    }
                }
                d.reject();
            },asyncStorageDelay);

            return d.promise();
        },
        
        // asynchronously add an element to the collection
        collection_add: function(collection, elem){
            var d = $.Deferred();

            var col_str = localStorage.getItem('collection_'+collection);
            var col_obj = JSON.parse(col_str);

            col_obj.data.push(elem);
            col_str = JSON.stringify(col_obj);

            localStorage.setItem('collection_'+collection, col_str)

            setTimeout(function(){
                d.resolve();
            },asyncStorageDelay);
            
            return d.promise();
        },
        
        // returns a deffered that provides a list of element in the collection 
        // matching the patterns *
        // patterns is a  dictionary of {'field':'pattern'}.
        // an object is said to match the patterns if one of his field has a related field in the
        // dictionary with a value that contains the 'pattern'. the list may be empty
        collection_find: function(collection, patterns){
            var d = $.Deferred();

            var col_str = localStorage.getItem('collection_'+collection)
            var col_obj = JSON.parse(col_str);
            var data = col_obj.data;
            var results = [];
            var lowerpatterns = {};
            for (field in patterns){
                lowerpatterns[field] = patterns[field].toLowerCase();
            }


            for(var i = 0; i < data.length; i++){
                var elem = data[i];
                for(field in lowerpatterns){
                    if(elem[field] && (''+elem[field]).toLowerCase().indexOf(lowerpatterns[field]) >= 0){
                        results.push(elem);
                        break;
                    }
                }
            }

            setTimeout(function(){
                d.resolve(results);
            },asyncStorageDelay);

            return d.promise();
        },
    };
})();

openerp.point_of_sale = function(session) {
    
    session.point_of_sale = {};

    var QWeb = session.web.qweb;
    var qweb_template = function(template) {
        return function(ctx) {
            return QWeb.render(template, _.extend({}, ctx,{
                'currency': pos.get('currency'),
                'format_amount': function(amount) {
                    if (pos.get('currency').position == 'after') {
                        return amount + ' ' + pos.get('currency').symbol;
                    } else {
                        return pos.get('currency').symbol + ' ' + amount;
                    }
                },
                }));
        };
    };
    var _t = session.web._t;

    /*
     Local store access. Read once from localStorage upon construction and persist on every change.
     There should only be one store active at any given time to ensure data consistency.
     */
    var Store = session.web.Class.extend({
        init: function() {
            this.data = {};
        },
        get: function(key, _default) {
            if (this.data[key] === undefined) {
                var stored = localStorage['oe_pos_' + key];
                if (stored)
                    this.data[key] = JSON.parse(stored);
                else
                    console.log('Store get: ',key, 'default: ',_default);
                    return _default;
            }
            console.log('Store get: ',key, 'value: ',this.data[key]);
            return this.data[key];
        },
        set: function(key, value) {
            console.log('Store set: ',key,' value: ',value);
            this.data[key] = value;
            localStorage['oe_pos_' + key] = JSON.stringify(value);
        },
        collection_new: function(collection, searchable_fields){
            return asyncStorage.collection_new(collection,searchable_fields);
        },
        collection_get: function(collection, field, name){
            return asyncStorage.collection_get(collection,field,name);
        },
        collection_add: function(collection, elem){
            return asyncStorage.collection_add(collection,elem);
        },
        collection_find: function(collection, patterns){
            return asyncStorage.collection_find(collection,patterns);
        }
    });
    
    /*
     Gets all the necessary data from the OpenERP web client (session, shop data etc.)
     */
    var Pos = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            this.store = new Store();
            this.ready = $.Deferred();
            this.flush_mutex = new $.Mutex();
            this.build_tree = _.bind(this.build_tree, this);
            this.session = session;
            var attributes = {
                'pending_operations': [],
                'currency': {symbol: '$', position: 'after'},
                'shop': {},
                'company': {},
                'user': {},
            };
            _.each(attributes, _.bind(function(def, attr) {
                var to_set = {};
                to_set[attr] = this.store.get(attr, def);
                this.set(to_set);
                this.bind('change:' + attr, _.bind(function(unused, val) {
                    this.store.set(attr, val);
                }, this));
            }, this));
            $.when(this.fetch('pos.category', ['name', 'parent_id', 'child_id']),
                this.fetch('product.product', ['name', 'list_price', 'pos_categ_id', 'taxes_id', 'product_image_small', 'ean13', 'id'], [['pos_categ_id', '!=', 'false']]),
                this.fetch('product.packaging', ['product_id', 'ean']),
                this.fetch('account.bank.statement', ['account_id', 'currency', 'journal_id', 'state', 'name'],
                    [['state', '=', 'open'], ['user_id', '=', this.session.uid]]),
                this.fetch('account.journal', ['auto_cash', 'check_dtls', 'currency', 'name', 'type']),
                this.fetch('account.tax', ['amount', 'price_include', 'type']),
                this.get_app_data())
                .pipe(_.bind(this.build_tree, this));
        },
        fetch: function(osvModel, fields, domain) {
            var dataSetSearch;
            var self = this;
            dataSetSearch = new session.web.DataSetSearch(this, osvModel, {}, domain);
            return dataSetSearch.read_slice(fields, 0).then(function(result) {
                return self.store.set(osvModel, result);
            });
        },
        get_app_data: function() {
            var self = this;
            return $.when(new session.web.Model("sale.shop").get_func("search_read")([]).pipe(function(result) {
                self.set({'shop': result[0]});
                var company_id = result[0]['company_id'][0];
                return new session.web.Model("res.company").get_func("read")(company_id, ['currency_id', 'name', 'phone']).pipe(function(result) {
                    self.set({'company': result});
                    var currency_id = result['currency_id'][0]
                    return new session.web.Model("res.currency").get_func("read")([currency_id],
                            ['symbol', 'position']).pipe(function(result) {
                        self.set({'currency': result[0]});
                        
                    });
                });
            }), new session.web.Model("res.users").get_func("read")(this.session.uid, ['name']).pipe(function(result) {
                self.set({'user': result});
            }));
        },
        pushOrder: function(record) {
            var ops = _.clone(this.get('pending_operations'));
            ops.push(record);
            this.set({pending_operations: ops});
            return this.flush();
        },
        flush: function() {
            return this.flush_mutex.exec(_.bind(function() {
                return this._int_flush();
            }, this));
        },
        _int_flush : function() {
            var ops = this.get('pending_operations');
            if (ops.length === 0)
                return $.when();
            var op = ops[0];
            /* we prevent the default error handler and assume errors
             * are a normal use case, except we stop the current iteration
             */
            return new session.web.Model("pos.order").get_func("create_from_ui")([op]).fail(function(unused, event) {
                event.preventDefault();
            }).pipe(_.bind(function() {
                console.debug('saved 1 record');
                var ops2 = this.get('pending_operations');
                this.set({'pending_operations': _.without(ops2, op)});
                return this._int_flush();
            }, this), function() {return $.when()});
        },
        categories: {},
        build_tree: function() {
            var c, id, _i, _len, _ref, _ref2;
            _ref = this.store.get('pos.category');
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
                    _ref3 = this.store.get('pos.category');
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
                    _ref3 = this.store.get('pos.category');
                    _results = [];
                    for (_j = 0, _len2 = _ref3.length; _j < _len2; _j++) {
                        c = _ref3[_j];
                        _results.push(c.id);
                    }
                    return _results;
                }).call(this)
            };
            return this.ready.resolve();
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

    /* global variable */
    var pos;

    /*
     ---
     Models
     ---
     */

    var CashRegister = Backbone.Model.extend({
    });

    var CashRegisterCollection = Backbone.Collection.extend({
        model: CashRegister,
    });

    var Product = Backbone.Model.extend({
    });

    var ProductCollection = Backbone.Collection.extend({
        model: Product,
    });

    var Category = Backbone.Model.extend({
    });

    var CategoryCollection = Backbone.Collection.extend({
        model: Category,
    });

    /*
     Each Order contains zero or more Orderlines (i.e. the content of the "shopping cart".)
     There should only ever be one Orderline per distinct product in an Order.
     To add more of the same product, just update the quantity accordingly.
     The Order also contains payment information.
     */
    var Orderline = Backbone.Model.extend({
        defaults: {
            quantity: 1,
            list_price: 0,
            discount: 0
        },
        initialize: function(attributes) {
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
            
            var products = pos.store.get('product.product');
            var product = _.detect(products, function(el) {return el.id === self.get('id');});
            var taxes_ids = product.taxes_id;
            var taxes =  pos.store.get('account.tax');
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

    var OrderlineCollection = Backbone.Collection.extend({
        model: Orderline,
    });

    // Every PaymentLine has all the attributes of the corresponding CashRegister.
    var Paymentline = Backbone.Model.extend({
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
                name: session.web.datetime_to_str(new Date()),
                statement_id: this.get('id'),
                account_id: (this.get('account_id'))[0],
                journal_id: (this.get('journal_id'))[0],
                amount: this.getAmount()
            };
        },
    });

    var PaymentlineCollection = Backbone.Collection.extend({
        model: Paymentline,
    });
    
    var Order = Backbone.Model.extend({
        defaults:{
            validated: false,
            step: 'products',
        },
        initialize: function(attributes){
            Backbone.Model.prototype.initialize.apply(this, arguments);
            this.set({
                creationDate:   new Date,
                orderLines:     new OrderlineCollection,
                paymentLines:   new PaymentlineCollection,
                name:           "Order " + this.generateUniqueId(),
            });
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
                var line = new Orderline(product.toJSON());
                console.log('orderline:',line,product.toJSON());
                this.get('orderLines').add(line);
                line.bind('killme', function() {
                    this.get('orderLines').remove(line);
                }, this);
            }
        },
        addPaymentLine: function(cashRegister) {
            var newPaymentline;
            newPaymentline = new Paymentline(cashRegister);
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

    var OrderCollection = Backbone.Collection.extend({
        model: Order,
    });

    var Shop = Backbone.Model.extend({
        initialize: function() {
            this.set({
                orders: new OrderCollection(),
                products: new ProductCollection()
            });
            this.set({
                cashRegisters: new CashRegisterCollection(pos.store.get('account.bank.statement')),
            });
            return (this.get('orders')).bind('remove', _.bind( function(removedOrder) {
                if ((this.get('orders')).isEmpty()) {
                    this.addAndSelectOrder(new Order);
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
    });

    /*
     The numpad handles both the choice of the property currently being modified
     (quantity, price or discount) and the edition of the corresponding numeric value.
     */
    var NumpadState = Backbone.Model.extend({
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

    /*
     ---
     Views
     ---
     */
    var NumpadWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.state = new NumpadState();
        },
        start: function() {
            this.state.bind('change:mode', this.changedMode, this);
            this.changedMode();
            this.$element.find('button#numpad-backspace').click(_.bind(this.clickDeleteLastChar, this));
            this.$element.find('button#numpad-minus').click(_.bind(this.clickSwitchSign, this));
            this.$element.find('button.number-char').click(_.bind(this.clickAppendNewChar, this));
            this.$element.find('button.mode-button').click(_.bind(this.clickChangeMode, this));
        },
        clickDeleteLastChar: function() {
            return this.state.deleteLastChar();
        },
        clickSwitchSign: function() {
            return this.state.switchSign();
        },
        clickAppendNewChar: function(event) {
            var newChar;
            newChar = event.currentTarget.innerText || event.currentTarget.textContent;
            return this.state.appendNewChar(newChar);
        },
        clickChangeMode: function(event) {
            var newMode = event.currentTarget.attributes['data-mode'].nodeValue;
            return this.state.changeMode(newMode);
        },
        changedMode: function() {
            var mode = this.state.get('mode');
            $('.selected-mode').removeClass('selected-mode');
            $(_.str.sprintf('.mode-button[data-mode="%s"]', mode), this.$element).addClass('selected-mode');
        },
    });
    /*
     Gives access to the payment methods (aka. 'cash registers')
     */
    var PaypadWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.shop = options.shop;
        },
        start: function() {
            this.$element.find('button').click(_.bind(this.performPayment, this));
        },
        performPayment: function(event) {
            if (this.shop.get('selectedOrder').get('step') === 'receipt')
                return;
            var cashRegister, cashRegisterCollection, cashRegisterId;
            /* set correct view */
            this.shop.get('selectedOrder').set({'step': 'payment'});

            cashRegisterId = event.currentTarget.attributes['cash-register-id'].nodeValue;
            cashRegisterCollection = this.shop.get('cashRegisters');
            cashRegister = cashRegisterCollection.find(_.bind( function(item) {
                return (item.get('id')) === parseInt(cashRegisterId, 10);
            }, this));
            return (this.shop.get('selectedOrder')).addPaymentLine(cashRegister);
        },
        renderElement: function() {
            this.$element.empty();
            return (this.shop.get('cashRegisters')).each(_.bind( function(cashRegister) {
                var button = new PaymentButtonWidget();
                button.model = cashRegister;
                button.appendTo(this.$element);
            }, this));
        }
    });
    var PaymentButtonWidget = session.web.OldWidget.extend({
        template_fct: qweb_template('pos-payment-button-template'),
        renderElement: function() {
            this.$element.html(this.template_fct({
                id: this.model.get('id'),
                name: (this.model.get('journal_id'))[1]
            }));
            return this;
        }
    });
    /*
     There are 3 steps in a POS workflow:
     1. prepare the order (i.e. chose products, quantities etc.)
     2. choose payment method(s) and amount(s)
     3. validae order and print receipt
     It should be possible to go back to any step as long as step 3 hasn't been completed.
     Modifying an order after validation shouldn't be allowed.
     */
    var StepSwitcher = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.shop = options.shop;
            this.change_order();
            this.shop.bind('change:selectedOrder', this.change_order, this);
        },
        change_order: function() {
            if (this.selected_order) {
                this.selected_order.unbind('change:step', this.change_step);
            }
            this.selected_order = this.shop.get('selectedOrder');
            if (this.selected_order) {
                this.selected_order.bind('change:step', this.change_step, this);
            }
            this.change_step();
        },
        change_step: function() {
            var new_step = this.selected_order ? this.selected_order.get('step') : 'products';
            $('.step-screen').hide();
            $('#' + new_step + '-screen').show();
        },
    });
    /*
     Shopping carts.
     */
    var OrderlineWidget = session.web.OldWidget.extend({
        tagName: 'tr',
        template_fct: qweb_template('pos-orderline-template'),
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.model.bind('change', _.bind( function() {
                this.refresh();
            }, this));
            this.model.bind('remove', _.bind( function() {
                this.$element.remove();
            }, this));
            this.order = options.order;
        },
        start: function() {
            this.$element.click(_.bind(this.clickHandler, this));
            this.refresh();
        },
        clickHandler: function() {
            this.select();
        },
        renderElement: function() {
            this.$element.html(this.template_fct(this.model.toJSON()));
            this.select();
        },
        refresh: function() {
            this.renderElement();
            var heights = _.map(this.$element.prevAll(), function(el) {return $(el).outerHeight();});
            heights.push($('#current-order thead').outerHeight());
            var position = _.reduce(heights, function(memo, num){ return memo + num; }, 0);
            $('#current-order').scrollTop(position);
        },
        select: function() {
            $('tr.selected').removeClass('selected');
            this.$element.addClass('selected');
            this.order.selected = this.model;
            this.on_selected();
        },
        on_selected: function() {},
    });

    var OrderWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.shop = options.shop;
            this.setNumpadState(options.numpadState);
            this.shop.bind('change:selectedOrder', this.changeSelectedOrder, this);
            this.bindOrderLineEvents();
        },
        setNumpadState: function(numpadState) {
        	if (this.numpadState) {
        		this.numpadState.unbind('setValue', this.setValue);
        	}
        	this.numpadState = numpadState;
        	if (this.numpadState) {
        		this.numpadState.bind('setValue', this.setValue, this);
        		this.numpadState.reset();
        	}
        },
        setValue: function(val) {
        	var param = {};
        	param[this.numpadState.get('mode')] = val;
        	var order = this.shop.get('selectedOrder');
        	if (order.get('orderLines').length !== 0) {
        	   order.selected.set(param);
        	} else {
        	    this.shop.get('selectedOrder').destroy();
        	}
        },
        changeSelectedOrder: function() {
            this.currentOrderLines.unbind();
            this.bindOrderLineEvents();
            this.renderElement();
        },
        bindOrderLineEvents: function() {
            this.currentOrderLines = (this.shop.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', this.addLine, this);
            this.currentOrderLines.bind('remove', this.renderElement, this);
        },
        addLine: function(newLine) {
            var line = new OrderlineWidget(null, {
                    model: newLine,
                    order: this.shop.get('selectedOrder')
            });
            line.on_selected.add(_.bind(this.selectedLine, this));
            this.selectedLine();
            line.appendTo(this.$element);
            this.updateSummary();
        },
        selectedLine: function() {
        	var reset = false;
        	if (this.currentSelected !== this.shop.get('selectedOrder').selected) {
        		reset = true;
        	}
        	this.currentSelected = this.shop.get('selectedOrder').selected;
        	if (reset && this.numpadState)
        		this.numpadState.reset();
            this.updateSummary();
        },
        renderElement: function() {
            this.$element.empty();
            this.currentOrderLines.each(_.bind( function(orderLine) {
                var line = new OrderlineWidget(null, {
                        model: orderLine,
                        order: this.shop.get('selectedOrder')
                });
            	line.on_selected.add(_.bind(this.selectedLine, this));
                line.appendTo(this.$element);
            }, this));
            this.updateSummary();
        },
        updateSummary: function() {
            var currentOrder, tax, total, totalTaxExcluded;
            currentOrder = this.shop.get('selectedOrder');
            total = currentOrder.getTotal();
            totalTaxExcluded = currentOrder.getTotalTaxExcluded();
            tax = currentOrder.getTax();
            $('#subtotal').html(totalTaxExcluded.toFixed(2)).hide().fadeIn();
            $('#tax').html(tax.toFixed(2)).hide().fadeIn();
            $('#total').html(total.toFixed(2)).hide().fadeIn();
        },
    });

    /*
     "Products" step.
     */
    var CategoryWidget = session.web.OldWidget.extend({
        start: function() {
            this.$element.find(".oe-pos-categories-list a").click(_.bind(this.changeCategory, this));
        },
        template_fct: qweb_template('pos-category-template'),
        renderElement: function() {
            var self = this;
            var c;
            this.$element.html(this.template_fct({
                breadcrumb: (function() {
                    var _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = self.ancestors.length; _i < _len; _i++) {
                        c = self.ancestors[_i];
                        _results.push(pos.categories[c]);
                    }
                    return _results;
                })(),
                categories: (function() {
                    var _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = self.children.length; _i < _len; _i++) {
                        c = self.children[_i];
                        _results.push(pos.categories[c]);
                    }
                    return _results;
                })()
            }));
        },
        changeCategory: function(a) {
            var id = $(a.target).data("category-id");
            this.on_change_category(id);
        },
        on_change_category: function(id) {},
    });

    var ProductWidget = session.web.OldWidget.extend({
        tagName:'li',
        template_fct: qweb_template('pos-product-template'),
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.shop = options.shop;
        },
        start: function(options) {
            $("a", this.$element).click(_.bind(this.addToOrder, this));
        },
        addToOrder: function(event) {
            /* Preserve the category URL */
            event.preventDefault();
            return (this.shop.get('selectedOrder')).addProduct(this.model);
        },
        renderElement: function() {
            this.$element.addClass("product");
            this.$element.html(this.template_fct(this.model.toJSON()));
            return this;
        },
    });

    var ProductListWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.shop = options.shop;
            this.shop.get('products').bind('reset', this.renderElement, this);
        },
        renderElement: function() {
            this.$element.empty();
            (this.shop.get('products')).each(_.bind( function(product) {
                var p = new ProductWidget(null, {
                        model: product,
                        shop: this.shop
                });
                p.appendTo(this.$element);
            }, this));
            return this;
        },
    });
    /*
     "Payment" step.
     */
    var PaymentlineWidget = session.web.OldWidget.extend({
        tagName: 'tr',
        template_fct: qweb_template('pos-paymentline-template'),
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.model.bind('change', this.changedAmount, this);
        },
        on_delete: function() {},
        changeAmount: function(event) {
            var newAmount;
            newAmount = event.currentTarget.value;
            if (newAmount && !isNaN(newAmount)) {
            	this.amount = parseFloat(newAmount);
                this.model.set({
                    amount: this.amount,
                });
            }
        },
        changedAmount: function() {
        	if (this.amount !== this.model.get('amount'))
        		this.renderElement();
        },
        renderElement: function() {
        	this.amount = this.model.get('amount');
            this.$element.html(this.template_fct({
                name: (this.model.get('journal_id'))[1],
                amount: this.amount,
            }));
            this.$element.addClass('paymentline');
            $('input', this.$element).keyup(_.bind(this.changeAmount, this));
            $('.delete-payment-line', this.$element).click(this.on_delete);
        },
    });

    var PaymentWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.shop = options.shop;
            this.shop.bind('change:selectedOrder', this.changeSelectedOrder, this);
            this.bindPaymentLineEvents();
            this.bindOrderLineEvents();
        },
        paymentLineList: function() {
            return this.$element.find('#paymentlines');
        },
        start: function() {
            $('button#validate-order', this.$element).click(_.bind(this.validateCurrentOrder, this));
            $('.oe-back-to-products', this.$element).click(_.bind(this.back, this));
        },
        back: function() {
            this.shop.get('selectedOrder').set({"step": "products"});
        },
        validateCurrentOrder: function() {
            var callback, currentOrder;
            currentOrder = this.shop.get('selectedOrder');
            $('button#validate-order', this.$element).attr('disabled', 'disabled');
            pos.pushOrder(currentOrder.exportAsJSON()).then(_.bind(function() {
                $('button#validate-order', this.$element).removeAttr('disabled');
                return currentOrder.set({
                    validated: true
                });
            }, this));
        },
        bindPaymentLineEvents: function() {
            this.currentPaymentLines = (this.shop.get('selectedOrder')).get('paymentLines');
            this.currentPaymentLines.bind('add', this.addPaymentLine, this);
            this.currentPaymentLines.bind('remove', this.renderElement, this);
            this.currentPaymentLines.bind('all', this.updatePaymentSummary, this);
        },
        bindOrderLineEvents: function() {
            this.currentOrderLines = (this.shop.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('all', this.updatePaymentSummary, this);
        },
        changeSelectedOrder: function() {
            this.currentPaymentLines.unbind();
            this.bindPaymentLineEvents();
            this.currentOrderLines.unbind();
            this.bindOrderLineEvents();
            this.renderElement();
        },
        addPaymentLine: function(newPaymentLine) {
            var x = new PaymentlineWidget(null, {
                    model: newPaymentLine
                });
            x.on_delete.add(_.bind(this.deleteLine, this, x));
            x.appendTo(this.paymentLineList());
        },
        renderElement: function() {
            this.paymentLineList().empty();
            this.currentPaymentLines.each(_.bind( function(paymentLine) {
                this.addPaymentLine(paymentLine);
            }, this));
            this.updatePaymentSummary();
        },
        deleteLine: function(lineWidget) {
        	this.currentPaymentLines.remove([lineWidget.model]);
        },
        updatePaymentSummary: function() {
            var currentOrder, dueTotal, paidTotal, remaining, remainingAmount;
            currentOrder = this.shop.get('selectedOrder');
            paidTotal = currentOrder.getPaidTotal();
            dueTotal = currentOrder.getTotal();
            this.$element.find('#payment-due-total').html(dueTotal.toFixed(2));
            this.$element.find('#payment-paid-total').html(paidTotal.toFixed(2));
            remainingAmount = dueTotal - paidTotal;
            remaining = remainingAmount > 0 ? 0 : (-remainingAmount).toFixed(2);
            $('#payment-remaining').html(remaining);
        },
        setNumpadState: function(numpadState) {
        	if (this.numpadState) {
        		this.numpadState.unbind('setValue', this.setValue);
        		this.numpadState.unbind('change:mode', this.setNumpadMode);
        	}
        	this.numpadState = numpadState;
        	if (this.numpadState) {
        		this.numpadState.bind('setValue', this.setValue, this);
        		this.numpadState.bind('change:mode', this.setNumpadMode, this);
        		this.numpadState.reset();
        		this.setNumpadMode();
        	}
        },
    	setNumpadMode: function() {
    		this.numpadState.set({mode: 'payment'});
    	},
        setValue: function(val) {
        	this.currentPaymentLines.last().set({amount: val});
        },
    });

    var ReceiptWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.shop = options.shop;
            this.user = pos.get('user');
            this.company = pos.get('company');
            this.shop_obj = pos.get('shop');
        },
        start: function() {
            this.shop.bind('change:selectedOrder', this.changeSelectedOrder, this);
            this.changeSelectedOrder();
        },
        renderElement: function() {
            this.$element.html(qweb_template('pos-receipt-view'));
            $('button#pos-finish-order', this.$element).click(_.bind(this.finishOrder, this));
            $('button#print-the-ticket', this.$element).click(_.bind(this.print, this));
        },
        print: function() {
            window.print();
        },
        finishOrder: function() {
            this.shop.get('selectedOrder').destroy();
        },
        changeSelectedOrder: function() {
            if (this.currentOrderLines)
                this.currentOrderLines.unbind();
            this.currentOrderLines = (this.shop.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', this.refresh, this);
            this.currentOrderLines.bind('change', this.refresh, this);
            this.currentOrderLines.bind('remove', this.refresh, this);
            if (this.currentPaymentLines)
                this.currentPaymentLines.unbind();
            this.currentPaymentLines = (this.shop.get('selectedOrder')).get('paymentLines');
            this.currentPaymentLines.bind('all', this.refresh, this);
            this.refresh();
        },
        refresh: function() {
            this.currentOrder = this.shop.get('selectedOrder');
            $('.pos-receipt-container', this.$element).html(qweb_template('pos-ticket')({widget:this}));
        },
    });

    var OrderButtonWidget = session.web.OldWidget.extend({
        tagName: 'li',
        template_fct: qweb_template('pos-order-selector-button-template'),
        init: function(parent, options) {
            this._super(parent);
            this.order = options.order;
            this.shop = options.shop;
            this.order.bind('destroy', _.bind( function() {
                this.destroy();
            }, this));
            this.shop.bind('change:selectedOrder', _.bind( function(shop) {
                var selectedOrder;
                selectedOrder = shop.get('selectedOrder');
                if (this.order === selectedOrder) {
                    this.setButtonSelected();
                }
            }, this));
        },
        start: function() {
            $('button.select-order', this.$element).click(_.bind(this.selectOrder, this));
            $('button.close-order', this.$element).click(_.bind(this.closeOrder, this));
        },
        selectOrder: function(event) {
            this.shop.set({
                selectedOrder: this.order
            });
        },
        setButtonSelected: function() {
            $('.selected-order').removeClass('selected-order');
            this.$element.addClass('selected-order');
        },
        closeOrder: function(event) {
            this.order.destroy();
        },
        renderElement: function() {
            this.$element.html(this.template_fct({widget:this}));
            this.$element.addClass('order-selector-button');
        }
    });

    var ToolbarWidget = session.web.Widget.extend({
        tagName: 'div',
        init: function(parent, options){
            this._super(parent,options);
        },
    });

    // A Widget that displays an onscreen keyboard.
    // There are two options when creating the widget :
    // 
    // * 'keyboard_model' : 'simple' | 'full' (default) 
    //   The 'full' emulates a PC keyboard, while 'simple' emulates an 'android' one.
    //
    // * 'input_selector  : (default: '.searchbox input') 
    //   defines the dom element that the keyboard will write to.
    // 
    // The widget is initially hidden. It can be shown with this.show(), and is 
    // automatically shown when the input_selector gets focused.
    var OnscreenKeyboardWidget = session.web.Widget.extend({
        tagName: 'div',
        
        init: function(parent, options){
            var self = this;

            this._super(parent,options);
            
            function get_option(opt,default_value){ 
                if(options){
                    return options[opt] || default_value;
                }else{
                    return default_value;
                }
            }

            this.keyboard_model = get_option('keyboard_model','full');
            this.template_simple = qweb_template('pos-onscreen-keyboard-simple-template');
            this.template_full   = qweb_template('pos-onscreen-keyboard-full-template');

            this.template_fct = function(){ 
                if( this.keyboard_model == 'full' ){
                    return this.template_full.apply(this,arguments);
                }else{
                    return this.template_simple.apply(this,arguments);
                }
            };

            this.input_selector = get_option('input_selector','.searchbox input');

            //show the keyboard when the input zone is clicked.
            $(this.input_selector).focus(function(){self.show();});

            //Keyboard state
            this.capslock = false;
            this.shift    = false;
            this.numlock  = false;
        },
        
        // Write a character to the input zone
        writeCharacter: function(character){
            var $input = $(this.input_selector);
            $input[0].value += character;
            $input.keydown();
            $input.keyup();
        },
        
        // Sends a 'return' character to the input zone. TODO
        sendReturn: function(){
        },
        
        // Removes the last character from the input zone.
        deleteCharacter: function(){
            var $input = $(this.input_selector);
            var input_value = $input[0].value;
            $input[0].value = input_value.substr(0, input_value.length - 1);
            $input.keydown();
            $input.keyup();
        },
        
        // Clears the content of the input zone.
        deleteAllCharacters: function(){
            var $input = $(this.input_selector);
            $input[0].value = "";
            $input.keydown();
            $input.keyup();
        },
        renderElement: function(){
            this.$element.html(this.template_fct());
        },
        
        // Makes the keyboard show and slide from the bottom of the screen.
        show:  function(){
            $('.keyboard_frame').show().animate({'height':'235px'}, 500, 'swing');
        },
        
        // Makes the keyboard hide by sliding to the bottom of the screen.
        hide:  function(){
            var self = this;
            var frame = $('.keyboard_frame');
            frame.animate({'height':'0'}, 500, 'swing', function(){ frame.hide(); self.reset(); });
        },
        
        //What happens when the shift key is pressed : toggle case, remove capslock
        toggleShift: function(){
            $('.letter').toggleClass('uppercase');
            $('.symbol span').toggle();
            
            self.shift = (self.shift === true) ? false : true;
            self.capslock = false;
        },
        
        //what happens when capslock is pressed : toggle case, set capslock
        toggleCapsLock: function(){
            $('.letter').toggleClass('uppercase');
            self.capslock = true;
        },
        
        //What happens when numlock is pressed : toggle symbols and numlock label 
        toggleNumLock: function(){
            $('.symbol span').toggle();
            $('.numlock span').toggle();
            self.numlock = (self.numlock === true ) ? false : true;
        },

        //After a key is pressed, shift is disabled. 
        removeShift: function(){
            if (self.shift === true) {
                $('.symbol span').toggle();
                if (this.capslock === false) $('.letter').toggleClass('uppercase');
                
                self.shift = false;
            }
        },

        // Resets the keyboard to its original state; capslock: false, shift: false, numlock: false
        reset: function(){
            if(this.shift){
                this.toggleShift();
            }
            if(this.capslock){
                this.toggleCapsLock();
            }
            if(this.numlock){
                this.toggleNumLock();
            }
        },

        //called after the keyboard is in the DOM, sets up the key bindings.
        start: function(){
            var self = this;

            //this.show();


            $('.close_button').click(function(){ 
                self.deleteAllCharacters();
                self.hide(); 
            });

            // Keyboard key click handling
            $('.keyboard li').click(function(){
                
                var $this = $(this),
                    character = $this.html(); // If it's a lowercase letter, nothing happens to this variable
                
                if ($this.hasClass('left-shift') || $this.hasClass('right-shift')) {
                    self.toggleShift();
                    return false;
                }
                
                if ($this.hasClass('capslock')) {
                    self.toggleCapsLock();
                    return false;
                }
                
                if ($this.hasClass('delete')) {
                    self.deleteCharacter();
                    return false;
                }

                if ($this.hasClass('numlock')){
                    self.toggleNumLock();
                    return false;
                }
                
                // Special characters
                if ($this.hasClass('symbol')) character = $('span:visible', $this).html();
                if ($this.hasClass('space')) character = ' ';
                if ($this.hasClass('tab')) character = "\t";
                if ($this.hasClass('return')) character = "\n";
                
                // Uppercase letter
                if ($this.hasClass('uppercase')) character = character.toUpperCase();
                
                // Remove shift once a key is clicked.
                self.removeShift();

                self.writeCharacter(character);
            });
        },
    });

    var ShopWidget = session.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.shop = options.shop;
        },
        start: function() {
            $('button#neworder-button', this.$element).click(_.bind(this.createNewOrder, this));

            (this.shop.get('orders')).bind('add', this.orderAdded, this);
            (this.shop.get('orders')).add(new Order);
            this.productListView = new ProductListWidget(null, {
                shop: this.shop
            });
            this.productListView.$element = $("#products-screen-ol");
            this.productListView.renderElement();
            this.productListView.start();
            this.paypadView = new PaypadWidget(null, {
                shop: this.shop
            });
            this.paypadView.$element = $('#paypad');
            this.paypadView.renderElement();
            this.paypadView.start();
            this.numpadView = new NumpadWidget(null);
            this.numpadView.$element = $('#numpad');
            this.numpadView.start();
            this.orderView = new OrderWidget(null, {
                shop: this.shop,
            });
            this.orderView.$element = $('#current-order-content');
            this.orderView.start();
            this.paymentView = new PaymentWidget(null, {
                shop: this.shop
            });
            this.paymentView.$element = $('#payment-screen');
            this.paymentView.renderElement();
            this.paymentView.start();
            this.receiptView = new ReceiptWidget(null, {
                shop: this.shop,
            });
            this.receiptView.replace($('#receipt-screen'));
            this.stepSwitcher = new StepSwitcher(this, {shop: this.shop});
            this.shop.bind('change:selectedOrder', this.changedSelectedOrder, this);
            this.changedSelectedOrder();
        },
        createNewOrder: function() {
            var newOrder;
            newOrder = new Order;
            (this.shop.get('orders')).add(newOrder);
            this.shop.set({
                selectedOrder: newOrder
            });
        },
        orderAdded: function(newOrder) {
            var newOrderButton;
            newOrderButton = new OrderButtonWidget(null, {
                order: newOrder,
                shop: this.shop
            });
            newOrderButton.appendTo($('#orders'));
            newOrderButton.selectOrder();
        },
        changedSelectedOrder: function() {
        	if (this.currentOrder) {
        		this.currentOrder.unbind('change:step', this.changedStep);
        	}
        	this.currentOrder = this.shop.get('selectedOrder');
        	this.currentOrder.bind('change:step', this.changedStep, this);
        	this.changedStep();
        },
        changedStep: function() {
        	var step = this.currentOrder.get('step');
        	this.orderView.setNumpadState(null);
        	this.paymentView.setNumpadState(null);
        	if (step === 'products') {
        		this.orderView.setNumpadState(this.numpadView.state);
        	} else if (step === 'payment') {
        		this.paymentView.setNumpadState(this.numpadView.state);
        	}
        },
    });

    var App = (function() {

        function App($element) {
            this.initialize($element);
        }

        App.prototype.initialize = function($element) {
            this.shop = new Shop;
            this.shopView = new ShopWidget(null, {
                shop: this.shop
            });
            this.shopView.$element = $element;
            this.shopView.start();
            this.categoryView = new CategoryWidget(null, 'products-screen-categories');
            this.categoryView.on_change_category.add_last(_.bind(this.category, this));
            this.category();

            this.onscreenKeyboard = new OnscreenKeyboardWidget(null,{keyboard_model:'simple'});
            this.onscreenKeyboard.appendTo($(".point-of-sale #content"));
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
            var c, products, self = this;

            id = !id ? 0 : id; 

            c = pos.categories[id];
            this.categoryView.ancestors = c.ancestors;
            this.categoryView.children = c.children;
            this.categoryView.renderElement();
            this.categoryView.start();

            allProducts = pos.store.get('product.product');
            allPackages = pos.store.get('product.packaging');
            products = pos.store.get('product.product').filter( function(p) {
                var _ref;
                return _ref = p.pos_categ_id[0], _.indexOf(c.subtree, _ref) >= 0;
            });
            (this.shop.get('products')).reset(products);

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
                        var selectedOrder = self.shop.get('selectedOrder');
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
                            selectedOrder.addProduct(new Product(scannedProductModel));
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
                    m = products.filter( function(p) {
                        return p.name.toLowerCase().indexOf(s) != -1;
                    });
                    $('.search-clear').fadeIn();
                } else {
                    m = products;
                    $('.search-clear').fadeOut();
                }
                return (self.shop.get('products')).reset(m);
            });
            return $('.search-clear').click( function() {
                (self.shop.get('products')).reset(products);
                $('.searchbox input').val('').focus();
                return $('.search-clear').fadeOut();
            });
        };
        return App;
    })();
    
    session.point_of_sale.SynchNotification = session.web.OldWidget.extend({
        template: "pos-synch-notification",
        init: function() {
            this._super.apply(this, arguments);
            this.nbr_pending = 0;
        },
        renderElement: function() {
            this._super.apply(this, arguments);
            $('.oe_pos_synch-notification-button', this.$element).click(this.on_synch);
        },
        on_change_nbr_pending: function(nbr_pending) {
            this.nbr_pending = nbr_pending;
            this.renderElement();
        },
        on_synch: function() {}
    });

    session.web.client_actions.add('pos.ui', 'session.point_of_sale.PointOfSale');
    session.point_of_sale.PointOfSale = session.web.OldWidget.extend({
        init: function() {
            this._super.apply(this, arguments);

            if (pos)
                throw "It is not possible to instantiate multiple instances "+
                    "of the point of sale at the same time.";
            pos = new Pos(this.session);
        },
        start: function() {
            var self = this;
            return pos.ready.then(_.bind(function() {
                this.renderElement();
                this.synch_notification = new session.point_of_sale.SynchNotification(this);
                this.synch_notification.replace($('.oe_pos_synch-notification', this.$element));
                this.synch_notification.on_synch.add(_.bind(pos.flush, pos));
                
                pos.bind('change:pending_operations', this.changed_pending_operations, this);
                this.changed_pending_operations();
                
                this.$element.find("#loggedas button").click(function() {
                    self.try_close();
                });

                pos.app = new App(self.$element);
                session.webclient.set_content_full_screen(true);
                
                if (pos.store.get('account.bank.statement').length === 0)
                    return new session.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_pos_open_statement']], ['res_id']).pipe(
                            _.bind(function(res) {
                        return this.rpc('/web/action/load', {'action_id': res[0]['res_id']}).pipe(_.bind(function(result) {
                            var action = result.result;
                            this.do_action(action);
                        }, this));
                    }, this));
            }, this));
        },
        render: function() {
            return qweb_template("PointOfSale")();
        },
        changed_pending_operations: function () {
            this.synch_notification.on_change_nbr_pending(pos.get('pending_operations').length);
        },
        try_close: function() {
            pos.flush().then(_.bind(function() {
                var close = _.bind(this.close, this);
                if (pos.get('pending_operations').length > 0) {
                    var confirm = false;
                    $(QWeb.render('pos-close-warning')).dialog({
                        resizable: false,
                        height:160,
                        modal: true,
                        title: "Warning",
                        buttons: {
                            "Yes": function() {
                                confirm = true;
                                $( this ).dialog( "close" );
                            },
                            "No": function() {
                                $( this ).dialog( "close" );
                            }
                        },
                        close: function() {
                            if (confirm)
                                close();
                        }
                    });
                } else {
                    close();
                }
            }, this));
        },
        close: function() {
            // remove barcode reader event listener
            $('body').undelegate('', 'keyup')

            return new session.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_pos_close_statement']], ['res_id']).pipe(
                    _.bind(function(res) {
                return this.rpc('/web/action/load', {'action_id': res[0]['res_id']}).pipe(_.bind(function(result) {
                    var action = result.result;
                    action.context = _.extend(action.context || {}, {'cancel_action': {type: 'ir.actions.client', tag: 'default_home'}});
                    this.do_action(action);
                }, this));
            }, this));
        },
        destroy: function() {
            session.webclient.set_content_full_screen(false);
            pos = undefined;
            this._super();
        }
    });
}
