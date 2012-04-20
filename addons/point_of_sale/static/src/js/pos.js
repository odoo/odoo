openerp.point_of_sale = function(instance) {

    instance.point_of_sale = {};

    var namespace = instance.point_of_sale;

    var posmodel;    //the global point of sale instance

    var QWeb = instance.web.qweb;

    var qweb_template = function(template) {
        return function(ctx) {
            return QWeb.render(template, _.extend({}, ctx,{
                'currency': posmodel.get('currency'),
                'format_amount': function(amount) {
                    if (posmodel.get('currency').position == 'after') {
                        return amount + ' ' + posmodel.get('currency').symbol;
                    } else {
                        return posmodel.get('currency').symbol + ' ' + amount;
                    }
                },
                }));
        };
    };
    var _t = instance.web._t;

    var LocalStorageDAO = instance.web.Class.extend({
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
    var PosModel = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            var  self = this;
            this.dao = new LocalStorageDAO();
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
                'user': {}
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
                .pipe(_.bind(this.build_tree, this));
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
            this.posmodel = attributes.posmodel;
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
            
            var product_list = self.posmodel.get('product_list');
            var product = _.detect(product_list, function(el) {return el.id === self.get('id');});
            var taxes_ids = product.taxes_id;
            var taxes =  self.posmodel.get('taxes');
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
                name: instance.web.datetime_to_str(new Date()),
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
            this.posmodel =     attributes.posmodel; //TODO put that in set and remember to use 'get' to read it ... 
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
                attr.posmodel = this.posmodel;
                var line = new Orderline(attr);
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
        initialize: function(attributes) {
            var self = this;
            this.set({
                orders: new OrderCollection(),
                products: new ProductCollection(),
            });
            this.posmodel = attributes.posmodel;
            this.set({
                cashRegisters: new CashRegisterCollection(this.posmodel.get('bank_statements')),
            });
            return (this.get('orders')).bind('remove', _.bind( function(removedOrder) {
                if ((this.get('orders')).isEmpty()) {
                    this.addAndSelectOrder(new Order({posmodel: self.posmodel}));
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
    var NumpadWidget = instance.web.OldWidget.extend({
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
    var PaypadWidget = instance.web.OldWidget.extend({
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
    var PaymentButtonWidget = instance.web.OldWidget.extend({
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
    var StepSwitcher = instance.web.OldWidget.extend({
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
    var OrderlineWidget = instance.web.OldWidget.extend({
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

    var OrderWidget = instance.web.OldWidget.extend({
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
    var CategoryWidget = instance.web.OldWidget.extend({
        init: function(parent, options){
            this._super(parent,options.element_id);
            this.posmodel = options.posmodel;
        },
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
                        _results.push(self.posmodel.categories[c]);
                    }
                    return _results;
                })(),
                categories: (function() {
                    var _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = self.children.length; _i < _len; _i++) {
                        c = self.children[_i];
                        _results.push(self.posmodel.categories[c]);
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

    var ProductWidget = instance.web.OldWidget.extend({
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

    var ProductListWidget = instance.web.OldWidget.extend({
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
    var PaymentlineWidget = instance.web.OldWidget.extend({
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

    var PaymentWidget = instance.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.shop = options.shop;
            this.posmodel = options.posmodel;
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
            this.posmodel.push_order(currentOrder.exportAsJSON()).then(_.bind(function() {
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

    var ReceiptWidget = instance.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.shop = options.shop;
            this.user = posmodel.get('user');
            this.company = posmodel.get('company');
            this.shop_obj = posmodel.get('shop');
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

    var OrderButtonWidget = instance.web.OldWidget.extend({
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

    var ActionButtonWidget = instance.web.Widget.extend({
        template:'pos-action-button',
        init: function(parent, options){
            this._super(parent, options);
            this.label = options.label || 'button';
            this.rightalign = options.rightalign || false;
            if(options.icon){
                this.icon = options.icon;
                this.template = 'pos-action-button-with-icon';
            }
        },
    });

    var ActionbarWidget = instance.web.Widget.extend({
        template:'pos-actionbar',
        init: function(parent, options){
            this._super(parent,options);
            this.left_button_list = [];
            this.right_button_list = [];
        },
        start: function(){
            console.log('hello world!');
            window.actionbarwidget = this;
        },
        destroyButtons:function(position){
            var button_list;
            if(position === 'left'){
                button_list = this.left_button_list;
                this.left_button_list = [];
            }else if (position === 'right'){
                button_list = this.right_button_list;
                this.right_button_list = [];
            }else{
                return this;
            }
            for(var i = 0; i < button_list.length; i++){
                button_list[i].destroy();
            }
            return this;
        },
        addNewButton: function(position,button_options){
            if(arguments.length == 2){
                var button_list;
                var $button_list;
                if(position === 'left'){ 
                    button_list = this.left_button_list;
                    $button_list = $('.pos-actionbar-left-region');
                }else if(position === 'right'){
                    button_list = this.right_button_list;
                    $button_list = $('.pos-actionbar-right-region');
                }
                var button = new ActionButtonWidget(this,button_options);
                button_list.push(button);
                button.appendTo($button_list);
            }else{
                for(var i = 1; i < arguments.length; i++){
                    this.addNewButton(position,arguments[i]);
                }
            }
            return this;
        }
        /*
        renderElement: function() {
            //this.$element.html(this.template_fct());
        },*/
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
    var OnscreenKeyboardWidget = instance.web.Widget.extend({
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

    var ShopWidget = instance.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.shop = options.shop;
            this.posmodel = options.posmodel;
        },
        start: function() {
            $('button#neworder-button', this.$element).click(_.bind(this.createNewOrder, this));

            (this.shop.get('orders')).bind('add', this.orderAdded, this);
            (this.shop.get('orders')).add(new Order({'posmodel':this.posmodel}));
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
                shop: this.shop,
                posmodel: this.posmodel,
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
            newOrder = new Order({'posmodel': this.posmodel});
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

        function App($element, posmodel) {
            this.initialize($element, posmodel);
        }

        App.prototype.initialize = function($element, posmodel) {
            this.posmodel = posmodel;
            this.shop = new Shop({'posmodel': posmodel});
            this.shopView = new ShopWidget(null, {
                shop: this.shop,
                'posmodel': posmodel,
            });
            this.shopView.$element = $element;
            this.shopView.start();
            this.categoryView = new CategoryWidget(null, {element_id: 'products-screen-categories', posmodel: posmodel} );
            this.categoryView.on_change_category.add_last(_.bind(this.category, this));
            this.category();

            this.onscreenKeyboard = new OnscreenKeyboardWidget(null,{keyboard_model:'simple'});
            this.onscreenKeyboard.appendTo($(".point-of-sale #content"));

            this.actionBar = new ActionbarWidget(null);
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

            c = this.posmodel.categories[id];
            this.categoryView.ancestors = c.ancestors;
            this.categoryView.children = c.children;
            this.categoryView.renderElement();
            this.categoryView.start();

            allProducts = this.posmodel.get('product_list');

            allPackages = this.posmodel.get('product.packaging');
            
            product_list = this.posmodel.get('product_list').filter( function(p) {
                var _ref;
                return _ref = p.pos_categ_id[0], _.indexOf(c.subtree, _ref) >= 0;
            });
            (this.shop.get('products')).reset(product_list);

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
                    m = product_list.filter( function(p) {
                        return p.name.toLowerCase().indexOf(s) != -1;
                    });
                    $('.search-clear').fadeIn();
                } else {
                    m = product_list;
                    $('.search-clear').fadeOut();
                }
                return (self.shop.get('products')).reset(m);
            });
            return $('.search-clear').click( function() {
                (self.shop.get('products')).reset(product_list);
                $('.searchbox input').val('').focus();
                return $('.search-clear').fadeOut();
            });
        };
        return App;
    })();
    
    instance.point_of_sale.SynchNotification = instance.web.OldWidget.extend({
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

    instance.web.client_actions.add('pos.ui', 'instance.point_of_sale.POSWidget');

    instance.point_of_sale.POSWidget = instance.web.OldWidget.extend({
        init: function() {
            this._super.apply(this, arguments);

            this.posmodel = new PosModel(this.session);

            posmodel = this.posmodel;
        },
        start: function() {
            var self = this;
            return self.posmodel.ready.then(_.bind(function() {
                this.renderElement();
                this.synch_notification = new instance.point_of_sale.SynchNotification(this);
                this.synch_notification.replace($('.oe_pos_synch-notification', this.$element));
                this.synch_notification.on_synch.add(_.bind(self.posmodel.flush, self.posmodel));
                
                self.posmodel.bind('change:nbr_pending_operations', this.changed_pending_operations, this);
                this.changed_pending_operations();
                
                this.$element.find("#loggedas button").click(function() {
                    self.try_close();
                });

                self.posmodel.app = new App(self.$element, self.posmodel);
                instance.webclient.set_content_full_screen(true);
                
                if (self.posmodel.get('bank_statements').length === 0)
                    return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_pos_open_statement']], ['res_id']).pipe(
                            _.bind(function(res) {
                        return this.rpc('/web/action/load', {'action_id': res[0]['res_id']}).pipe(_.bind(function(result) {
                            var action = result.result;
                            this.do_action(action);
                        }, this));
                    }, this));
            }, this));
        },
        render: function() {
            return qweb_template("POSWidget")();
        },
        changed_pending_operations: function () {
            var self = this;
            this.synch_notification.on_change_nbr_pending(self.posmodel.get('nbr_pending_operations').length);
        },
        try_close: function() {
            var self = this;
            self.posmodel.flush().then(_.bind(function() {
                var close = _.bind(this.close, this);
                if (self.posmodel.get('nbr_pending_operations').length > 0) {
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

            return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_pos_close_statement']], ['res_id']).pipe(
                    _.bind(function(res) {
                return this.rpc('/web/action/load', {'action_id': res[0]['res_id']}).pipe(_.bind(function(result) {
                    var action = result.result;
                    action.context = _.extend(action.context || {}, {'cancel_action': {type: 'ir.actions.client', tag: 'default_home'}});
                    this.do_action(action);
                }, this));
            }, this));
        },
        destroy: function() {
            instance.webclient.set_content_full_screen(false);
            self.posmodel = undefined;
            this._super();
        }
    });
}
