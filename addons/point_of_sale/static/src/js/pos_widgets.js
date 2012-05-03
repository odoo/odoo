function openerp_pos_widgets(module, instance){ //module is instance.point_of_sale
    var QWeb = instance.web.qweb;

    var qweb_template = function(template,pos){
        return function(ctx){
            if(!pos){  //this is a huge hack that needs to be removed ... TODO
                var HackPosModel = Backbone.Model.extend({
                    initialize:function(){
                        this.set({
                            'currency': {symbol: '$', position: 'after'},
                        });
                    },
                });
                pos = new HackPosModel();
            }
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

    module.NumpadWidget = instance.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.state = new module.NumpadState();
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
    module.PaypadWidget = instance.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.pos = options.pos;
        },
        start: function() {
            this.$element.find('button').click(_.bind(this.performPayment, this));
        },
        performPayment: function(event) {
            if (this.pos.get('selectedOrder').get('screen') === 'receipt')
                return;
            var cashRegister, cashRegisterCollection, cashRegisterId;
            /* set correct view */
            this.pos.screen_selector.set_current_screen('payment');

            cashRegisterId = event.currentTarget.attributes['cash-register-id'].nodeValue;
            cashRegisterCollection = this.pos.get('cashRegisters');
            cashRegister = cashRegisterCollection.find(_.bind( function(item) {
                return (item.get('id')) === parseInt(cashRegisterId, 10);
            }, this));
            return (this.pos.get('selectedOrder')).addPaymentLine(cashRegister);
        },
        renderElement: function() {
            this.$element.empty();
            return (this.pos.get('cashRegisters')).each(_.bind( function(cashRegister) {
                var button = new module.PaymentButtonWidget();
                button.model = cashRegister;
                button.appendTo(this.$element);
            }, this));
        }
    });

    module.PaymentButtonWidget = instance.web.OldWidget.extend({
        template_fct: qweb_template('pos-payment-button-template'),
        renderElement: function() {
            this.$element.html(this.template_fct({
                id: this.model.get('id'),
                name: (this.model.get('journal_id'))[1]
            }));
            return this;
        }
    });

// ---------- "Shopping Carts" ----------

    module.OrderlineWidget = instance.web.OldWidget.extend({
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

    module.OrderWidget = instance.web.OldWidget.extend({
        init: function(parent, options) {
            this._super(parent);
            this.pos = options.pos;
            this.setNumpadState(options.numpadState);
            this.pos.bind('change:selectedOrder', this.changeSelectedOrder, this);
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
        	var order = this.pos.get('selectedOrder');
        	if (order.get('orderLines').length !== 0) {
        	   order.selected.set(param);
        	} else {
        	    this.pos.get('selectedOrder').destroy();
        	}
        },
        changeSelectedOrder: function() {
            this.currentOrderLines.unbind();
            this.bindOrderLineEvents();
            this.renderElement();
        },
        bindOrderLineEvents: function() {
            this.currentOrderLines = (this.pos.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', this.addLine, this);
            this.currentOrderLines.bind('remove', this.renderElement, this);
        },
        addLine: function(newLine) {
            var line = new module.OrderlineWidget(null, {
                    model: newLine,
                    order: this.pos.get('selectedOrder')
            });
            line.on_selected.add(_.bind(this.selectedLine, this));
            this.selectedLine();
            line.appendTo(this.$element);
            this.updateSummary();
        },
        selectedLine: function() {
        	var reset = false;
        	if (this.currentSelected !== this.pos.get('selectedOrder').selected) {
        		reset = true;
        	}
        	this.currentSelected = this.pos.get('selectedOrder').selected;
        	if (reset && this.numpadState)
        		this.numpadState.reset();
            this.updateSummary();
        },
        renderElement: function() {
            this.$element.empty();
            this.currentOrderLines.each(_.bind( function(orderLine) {
                var line = new module.OrderlineWidget(null, {
                        model: orderLine,
                        order: this.pos.get('selectedOrder')
                });
            	line.on_selected.add(_.bind(this.selectedLine, this));
                line.appendTo(this.$element);
            }, this));
            this.updateSummary();
        },
        updateSummary: function() {
            var currentOrder, tax, total, totalTaxExcluded;
            currentOrder = this.pos.get('selectedOrder');
            total = currentOrder.getTotal();
            totalTaxExcluded = currentOrder.getTotalTaxExcluded();
            tax = currentOrder.getTax();
            $('#subtotal').html(totalTaxExcluded.toFixed(2)).hide().fadeIn();
            $('#tax').html(tax.toFixed(2)).hide().fadeIn();
            $('#total').html(total.toFixed(2)).hide().fadeIn();
        },
    });

// ---------- Product Screen ----------


    module.ProductWidget = instance.web.Widget.extend({
        tagName:'li',
        template_fct: qweb_template('pos-product-template'),
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.pos = options.pos;
        },
        start: function(options) {
            $("a", this.$element).click(_.bind(this.addToOrder, this));
        },
        addToOrder: function(event) {
            /* Preserve the category URL */
            event.preventDefault();
            return (this.pos.get('selectedOrder')).addProduct(this.model);
        },
        renderElement: function() {
            this.$element.addClass("product");
            this.$element.html(this.template_fct(this.model.toJSON()));
            return this;
        },
    });

// ---------- "Payment" step. ----------

    module.PaymentlineWidget = instance.web.OldWidget.extend({
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

    module.OrderButtonWidget = instance.web.OldWidget.extend({
        tagName: 'li',
        template_fct: qweb_template('pos-order-selector-button-template'),
        init: function(parent, options) {
            this._super(parent);
            this.order = options.order;
            this.pos = options.pos;
            this.order.bind('destroy', _.bind( function() {
                this.destroy();
            }, this));
            this.pos.bind('change:selectedOrder', _.bind( function(pos) {
                var selectedOrder;
                selectedOrder = pos.get('selectedOrder');
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
            this.pos.set({
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

    module.ActionButtonWidget = instance.web.Widget.extend({
        template:'pos-action-button',
        init: function(parent, options){
            this._super(parent, options);
            this.label = options.label || 'button';
            this.rightalign = options.rightalign || false;
            this.click_action = options.click;
            if(options.icon){
                this.icon = options.icon;
                this.template = 'pos-action-button-with-icon';
            }
        },
        start: function(){
            if(this.click_action){
                this.$element.click(_.bind(this.click_action, this));
            }
        },
    });

    module.ActionbarWidget = instance.web.Widget.extend({
        template:'pos-actionbar',
        init: function(parent, options){
            this._super(parent,options);
            this.left_button_list = [];
            this.right_button_list = [];
        },
        start: function(){
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
                var button = new module.ActionButtonWidget(this,button_options);
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

// ---------- Screens Widgets ----------

    module.ScreenWidget = instance.web.Widget.extend({
        init: function(parent, options){
            this._super(parent, options);
        },
        show: function(){
            if(this.$element){
                this.$element.show();
            }
        },
        hide: function(){
            if(this.$element){
                this.$element.hide();
            }
        },
    });

    module.ScreenSelector = instance.web.Class.extend({
        init: function(options){
            this.pos = options.pos;
            this.screen_set = options.screen_set || {};
            this.current_screen = options.current_screen ? this.screen_set[options.current_screen] : undefined;
            this.default_screen = options.default_screen;
            
            var current = null;
            for(screen_name in this.screen_set){
                var screen = this.screen_set[screen_name];
                if(screen === this.current_screen){
                    current = screen;
                }else{
                    screen.hide();
                }
            }
            if(current){
                current.show();
            }

            this.selected_order = this.pos.get('selectedOrder');
            this.pos.bind('change:selectedOrder', this.load_saved_screen, this);
        },
        add_screen: function(screen_name, screen){
            screen.hide();
            this.screen_set[screen_name] = screen;
            return this;
        },
        load_saved_screen:  function(){
            if(this.selected_order != this.pos.get('selectedOrder')){
                var screen = this.pos.get('selectedOrder').get('screen') || this.default_screen;
                this.selected_order = this.pos.get('selectedOrder');
                this.set_current_screen(screen);
            }
        },
        set_current_screen: function(screen_name){
            var screen = this.screen_set[screen_name];
            
            this.pos.get('selectedOrder').set({'screen':screen_name});

            console.log('Set Current Screen: '+screen_name+' :',screen,'old:',this.current_screen);
            if(screen && screen !== this.current_screen){
                if(this.current_screen){
                    this.current_screen.hide();
                }
                this.current_screen = screen;
                this.current_screen.show();
            }
        },
    });

    module.PaymentScreenWidget = module.ScreenWidget.extend({
        template_fct: qweb_template('PaymentScreenWidget'),
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.pos = options.pos;
            this.pos_widget = options.pos_widget;
            this.pos.bind('change:selectedOrder', this.changeSelectedOrder, this);
            this.bindPaymentLineEvents();
            this.bindOrderLineEvents();
        },
        show: function(){
            this._super();
            this.setNumpadState(this.pos_widget.numpadView.state);
        },
        hide: function(){
            this._super();
            this.pos_widget.orderView.setNumpadState(null);
            this.pos_widget.payment_screen.setNumpadState(null);
        },
        paymentLineList: function() {
            return this.$element.find('#paymentlines');
        },
        back: function() {
            console.log('back');
            this.pos.screen_selector.set_current_screen('products');
        },
        validateCurrentOrder: function() {
            var callback, currentOrder;
            currentOrder = this.pos.get('selectedOrder');
            $('button#validate-order', this.$element).attr('disabled', 'disabled');
            this.pos.push_order(currentOrder.exportAsJSON()).then(_.bind(function() {
                $('button#validate-order', this.$element).removeAttr('disabled');
                return currentOrder.set({
                    validated: true
                });
            }, this));
        },
        bindPaymentLineEvents: function() {
            this.currentPaymentLines = (this.pos.get('selectedOrder')).get('paymentLines');
            this.currentPaymentLines.bind('add', this.addPaymentLine, this);
            this.currentPaymentLines.bind('remove', this.renderElement, this);
            this.currentPaymentLines.bind('all', this.updatePaymentSummary, this);
        },
        bindOrderLineEvents: function() {
            this.currentOrderLines = (this.pos.get('selectedOrder')).get('orderLines');
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
            var x = new module.PaymentlineWidget(null, {
                    model: newPaymentLine
                });
            x.on_delete.add(_.bind(this.deleteLine, this, x));
            x.appendTo(this.paymentLineList());
        },
        renderElement: function() {
            this._super();
            this.$element.html(this.template_fct());
            this.paymentLineList().empty();
            this.currentPaymentLines.each(_.bind( function(paymentLine) {
                this.addPaymentLine(paymentLine);
            }, this));
            this.updatePaymentSummary();
            $('button#validate-order', this.$element).click(_.bind(this.validateCurrentOrder, this));
            $('.oe-back-to-products', this.$element).click(_.bind(this.back, this));
        },
        deleteLine: function(lineWidget) {
        	this.currentPaymentLines.remove([lineWidget.model]);
        },
        updatePaymentSummary: function() {
            var currentOrder, dueTotal, paidTotal, remaining, remainingAmount;
            currentOrder = this.pos.get('selectedOrder');
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

    module.ReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'ReceiptScreenWidget',
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.pos = options.pos;
            this.pos = options.pos;
            this.user = this.pos.get('user');
            this.company = this.pos.get('company');
            this.shop_obj = this.pos.get('shop');
        },
        start: function() {
            this.pos.bind('change:selectedOrder', this.changeSelectedOrder, this);
            this.changeSelectedOrder();
            $('button#pos-finish-order', this.$element).click(_.bind(this.finishOrder, this));
            $('button#print-the-ticket', this.$element).click(_.bind(this.print, this));
        },
        print: function() {
            window.print();
        },
        finishOrder: function() {
            this.pos.get('selectedOrder').destroy();
        },
        changeSelectedOrder: function() {
            if (this.currentOrderLines)
                this.currentOrderLines.unbind();
            this.currentOrderLines = (this.pos.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', this.refresh, this);
            this.currentOrderLines.bind('change', this.refresh, this);
            this.currentOrderLines.bind('remove', this.refresh, this);
            if (this.currentPaymentLines)
                this.currentPaymentLines.unbind();
            this.currentPaymentLines = (this.pos.get('selectedOrder')).get('paymentLines');
            this.currentPaymentLines.bind('all', this.refresh, this);
            this.refresh();
        },
        refresh: function() {
            this.currentOrder = this.pos.get('selectedOrder');
            $('.pos-receipt-container', this.$element).html(qweb_template('pos-ticket')({widget:this}));
        },
    });

    module.WelcomeScreenWidget = module.ScreenWidget.extend({
    });

    module.ScanProductScreenWidget = module.ScreenWidget.extend({
    });

    module.ProductCategoriesWidget = instance.web.Widget.extend({
        init: function(parent, options){
            this._super(parent);
            this.pos = options.pos;
            this.on_change_category.add_last(_.bind(this.search_and_categories, this));
            this.search_and_categories(); 
        },
        start: function() {
            this.search_and_categories(); 
            this.$element.find(".oe-pos-categories-list a").click(_.bind(this.changeCategory, this));
        },
        template_fct: qweb_template('ProductCategoriesWidget'),
        template:'ProductCategoriesWidget',
        renderElement: function() {
            var self = this;
            var c;
            this.$element.empty();
            this.$element.html(QWeb.render(this.template, {
                breadcrumb: (function() {
                    var _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = self.ancestors.length; _i < _len; _i++) {
                        c = self.ancestors[_i];
                        _results.push(self.pos.categories[c]);
                    }
                    return _results;
                })(),
                categories: (function() {
                    var _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = self.children.length; _i < _len; _i++) {
                        c = self.children[_i];
                        _results.push(self.pos.categories[c]);
                    }
                    return _results;
                })()
            }));
        },
        changeCategory: function(a) {
            var id = $(a.target).data("category-id");
            this.on_change_category(id);
        },
        search_and_categories: function(id){
            var self = this,
                c,
                product_list,
                allProducts,
                allPackages;

            id = id || 0;

            c = this.pos.categories[id];
            this.ancestors = c.ancestors;
            this.children = c.children;
            this.renderElement();

            allProducts = this.pos.get('product_list');

            allPackages = this.pos.get('product.packaging');

            product_list = this.pos.get('product_list').filter( function(p){
                var _ref = p.pos_categ_id[0];
                return _.indexOf(c.subtree, _ref) >= 0;
            });

            this.pos.get('products').reset(product_list);

            this.$element.find('.searchbox input').keyup(function(){
                var results, search_str;
                search_str = $(this).val().toLowerCase();
                if(search_str){
                    results = product_list.filter( function(p){
                        return p.name.toLowerCase().indexOf(search_str) != -1;
                    });
                    self.$element.find('.search-clear').fadeIn();
                }else{
                    results = product_list;
                    self.$element.find('.search-clear').fadeOut();
                }
                self.pos.get('products').reset(results);
            });

            this.$element.find('.search-clear').click(function(){
                self.pos.get('products').reset(product_list);
                self.$element.find('.searchbox input').val('').focus();
                self.$element.find('.search-clear').fadeOut();
            });
        },
        on_change_category: function(id) {},
    });

    module.ProductListWidget = module.ScreenWidget.extend({
        template:'ProductListWidget',
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.pos = options.pos;
            this.pos.get('products').bind('reset', this.renderElement, this);
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.pos.get('products').chain().map(function(product) {
                return new module.ProductWidget(this, {
                        model: product,
                        pos: self.pos
                })
            }).invoke('appendTo', this.$element);
            return this;
        },
    });

    module.SearchProductScreenWidget = module.ScreenWidget.extend({
        template:'SearchProductScreenWidget',
        init: function(parent, options){
            this._super(parent,options);
            options = options || {};
            this.pos = options.pos;
            this.pos_widget = options.pos_widget;
        },
        start: function(){
            this.product_categories_widget = new module.ProductCategoriesWidget(null,{
                pos:this.pos,
            });
            this.product_categories_widget.replace($('.placeholder-ProductCategoriesWidget'));

            this.product_list_widget = new module.ProductListWidget(null,{
                pos:this.pos,
            });
            this.product_list_widget.replace($('.placeholder-ProductListWidget'));
        },
        show: function(){
            this._super();
            this.pos_widget.orderView.setNumpadState(this.pos_widget.numpadView.state);
        },
        hide: function(){
            this._super();
            this.pos_widget.orderView.setNumpadState(null);
            this.pos_widget.payment_screen.setNumpadState(null);
        },

    });

    module.ScaleInviteScreenWidget = module.ScreenWidget.extend({
    });

    module.ScaleProductSelectionScreenWidget = module.ScreenWidget.extend({
    });

    module.AskForMoneyScreenWidget =  module.ScreenWidget.extend({
    });


// ---------- PopUp Widgets ----------

    module.PopUp = instance.web.Widget.extend({
        close: function(){},
    });

    module.HelpPopUp = module.PopUp.extend({
    });

    module.ErrorPopUp = module.PopUp.extend({
    });

    module.TicketOrInvoicePopUp = module.PopUp.extend({
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

    module.OnscreenKeyboardWidget = instance.web.Widget.extend({
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

    module.SynchNotification = instance.web.OldWidget.extend({
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

    module.PosWidget = instance.web.OldWidget.extend({
        init: function() { 
            this._super.apply(this, arguments);
            this.pos = new module.PosModel(this.session);
        },
        start: function() {
            var self = this;
            return self.pos.ready.then(_.bind(function() {
                this.renderElement();
                this.synch_notification = new module.SynchNotification(this);
                this.synch_notification.replace($('.oe_pos_synch-notification', this.$element));
                this.synch_notification.on_synch.add(_.bind(self.pos.flush, self.pos));
                
                self.pos.bind('change:nbr_pending_operations', this.changed_pending_operations, this);
                this.changed_pending_operations();
                
                this.$element.find("#loggedas button").click(function() {
                    self.try_close();
                });

                this.buildWidgets();

                instance.webclient.set_content_full_screen(true);
                
                if (self.pos.get('bank_statements').length === 0)
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
        buildWidgets: function() {
            $('button#neworder-button', this.$element).click(_.bind(this.createNewOrder, this));

            (this.pos.get('orders')).bind('add', this.orderAdded, this);
            (this.pos.get('orders')).add(new module.Order({'pos':this.pos}));
            

            this.search_product_screen = new module.SearchProductScreenWidget(this,{
                pos: this.pos,
                pos_widget: this,
            });
            this.search_product_screen.appendTo($('#rightpane'));


            this.receipt_screen = new module.ReceiptScreenWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.receipt_screen.appendTo($('#rightpane'));


            this.payment_screen = new module.PaymentScreenWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.payment_screen.appendTo($('#rightpane'));

            this.paypadView = new module.PaypadWidget(null, {
                pos: this.pos
            });
            this.paypadView.$element = $('#paypad');
            this.paypadView.renderElement();
            this.paypadView.start();
            this.numpadView = new module.NumpadWidget(null);
            this.numpadView.$element = $('#numpad');
            this.numpadView.start();
            this.orderView = new module.OrderWidget(null, {
                pos: this.pos,
            });
            this.orderView.$element = $('#current-order-content');
            this.orderView.start();
            
            this.pos.screen_selector = new module.ScreenSelector({
                pos: this.pos,
                screen_set:{
                    'products': this.search_product_screen,
                    'payment' : this.payment_screen,
                    'receipt' : this.receipt_screen,
                },
                current_screen: 'products',
                default_screen: 'products',
            });

            this.onscreenKeyboard = new module.OnscreenKeyboardWidget(null, {
                'keyboard_model': 'simple'
            });
            this.onscreenKeyboard.appendTo($(".point-of-sale #content"));

            this.action_bar = new module.ActionbarWidget(null);
            this.action_bar.appendTo($(".point-of-sale #content"));
            this.action_bar.addNewButton('left',{
                label : 'Hello World',
                icon  : '/point_of_sale/static/src/img/icons/png48/face-monkey.png',
                click : function(){ console.log("Hello World!"); } 
            });

            this.pos.barcode_reader.connect();
            
        },
        createNewOrder: function() {
            var newOrder;
            newOrder = new module.Order({'pos': this.pos});
            (this.pos.get('orders')).add(newOrder);
            this.pos.set({
                selectedOrder: newOrder
            });
        },
        orderAdded: function(newOrder) {
            var newOrderButton;
            newOrderButton = new module.OrderButtonWidget(null, {
                order: newOrder,
                pos: this.pos
            });
            newOrderButton.appendTo($('#orders'));
            newOrderButton.selectOrder();
        },
        changed_pending_operations: function () {
            var self = this;
            this.synch_notification.on_change_nbr_pending(self.pos.get('nbr_pending_operations').length);
        },
        try_close: function() {
            var self = this;
            self.pos.flush().then(_.bind(function() {
                var close = _.bind(this.close, this);
                if (self.pos.get('nbr_pending_operations').length > 0) {
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
            this.pos.barcode_reader.disconnect();

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
            self.pos = undefined;
            this._super();
        }
    });
}
