
// this file contains the screens definitions. Screens are the
// content of the right pane of the pos, containing the main functionalities. 
// screens are contained in the PosWidget, in pos_widget.js
// all screens are present in the dom at all time, but only one is shown at the
// same time. 
//
// transition between screens is made possible by the use of the screen_selector,
// which is responsible of hiding and showing the screens, as well as maintaining
// the state of the screens between different orders.
//
// all screens inherit from ScreenWidget. the only addition from the base widgets
// are show() and hide() which shows and hides the screen but are also used to 
// bind and unbind actions on widgets and devices. The screen_selector guarantees
// that only one screen is shown at the same time and that show() is called after all
// hide()s

function openerp_pos_screens(module, instance){ //module is instance.point_of_sale
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

    module.ScreenWidget = instance.web.Widget.extend({
        init: function(parent, options){
            this._super(parent, options);
            options = options || {};
            this.pos = options.pos;
            this.pos_widget = options.pos_widget;
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
            if(this.pos.barcode_reader){
                this.pos.barcode_reader.reset_action_callbacks();
            }
            if(this.pos_widget.action_bar){
                this.pos_widget.action_bar.destroy_buttons();
            }
        },
    });

    module.ScaleInviteScreenWidget = module.ScreenWidget.extend({
        template:'ScaleInviteScreenWidget',
        show: function(){
            this._super();
            var self = this;

            self.pos.proxy.weighting_start();

            var intervalID = setInterval(function(){
                var weight = self.pos.proxy.weighting_read_kg();
                if(weight > 0.001){
                    clearInterval(intervalID);
                    self.pos.screen_selector.set_current_screen('scale_product');
                }
            },500);

            this.pos_widget.action_bar.add_new_button(
                {
                    label: 'help',
                    click: function(){ //TODO Show help popup
                    }
                },{
                    label: 'back',
                    click: function(){  //TODO Go to ask for weighting screen
                        clearInterval(intervalID);
                        self.pos.proxy.weighting_end();
                        self.pos.screen_selector.set_current_screen('scan');
                    }
                }
            );
        },
    });

    module.ScaleProductScreenWidget = module.ScreenWidget.extend({
        template:'ScaleProductSelectionScreenWidget',
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
            var self = this;
            this.pos_widget.orderView.setNumpadState(this.pos_widget.numpadView.state);
            this.pos_widget.action_bar.add_new_button(
                {
                    label: 'help',
                    click: function(){ //TODO Show help popup
                    }
                },{
                    label: 'back',
                    click: function(){
                        self.pos.screen_selector.set_current_screen('scan');
                    }
                }
            );
            this.pos.barcode_reader.set_action_callbacks({
                'cashier': function(ean){
                    //TODO 'switch to cashier mode'
                    self.proxy.cashier_mode_activated();
                },
            });
        },
        hide: function(){
            this._super();
            this.pos_widget.orderView.setNumpadState(null);
            this.pos_widget.payment_screen.setNumpadState(null);
        },

    });

    module.ClientPaymentScreenWidget =  module.ScreenWidget.extend({
        template:'ClientPaymentScreenWidget',
        show: function(){
            this._super();
            var self = this;

            this.pos.proxy.payment_request(0,'card','info');    //TODO TOTAL

            var intervalID = setInterval(function(){
                var payment = self.pos.proxy.is_payment_accepted();
                if(payment === 'payment_accepted'){
                    clearInterval(intervalID);
                    //TODO process the payment stuff
                    self.pos.proxy.transaction_end();
                    self.pos.screen_selector.set_current_screen('welcome');
                }else if(payment === 'payment_rejected'){
                    clearInterval(intervalID);
                    //TODO show a tryagain thingie ? 
                }
            },500);

            this.pos_widget.action_bar.add_new_button(
                {
                    label: 'help',
                    click: function(){ //TODO Show help popup
                    }
                },{
                    label: 'back',
                    click: function(){  //TODO Go to ask for weighting screen
                        clearInterval(intervalID);
                        self.pos.proxy.payment_canceled();
                        self.pos.screen_selector.set_current_screen('scan');
                    }
                }
            );

            this.pos.barcode_reader.set_action_callbacks({
                'cashier': function(ean){
                    //TODO 'switch to cashier mode'
                    clearInterval(intervalID);
                    self.proxy.cashier_mode_activated();
                    self.pos.screen_selector.set_current_screen('products');
                },
            });
        },
    });

    module.WelcomeScreenWidget = module.ScreenWidget.extend({
        template:'WelcomeScreenWidget',
        show: function(){
            this._super();
            var self = this;
            this.pos_widget.action_bar.add_new_button(
                {
                    label:'scan',
                    click: function(){
                        self.pos.screen_selector.set_current_screen('scan');
                    }
                },{
                    label: 'help',
                    click: function(){ //TODO Show help popup
                    }
                },{
                    label: 'peser',
                    click: function(){  //TODO Go to ask for weighting screen
                        self.pos.screen_selector.set_current_screen('scale_invite');
                    }
                }
            );
            this.pos.barcode_reader.set_action_callbacks({
                'product': function(ean){
                    self.proxy.transaction_start(); 
                    self.pos.barcode_reader.scan_product_callback(ean);
                    self.pos.screen_selector.set_current_screen('products');
                },
                'cashier': function(ean){
                    //TODO 'switch to cashier mode'
                    self.proxy.cashier_mode_activated();
                    self.pos.screen_selector.set_current_screen('products');
                },
                'client': function(ean){
                    self.proxy.transaction_start(); 
                    //TODO 'log the client'
                    self.pos.screen_selector.set_current_screen('products');
                },
                'discount': function(ean){
                    // TODO : what to do in this case ????
                },
            });
        },
        hide: function(){
            this._super();
            this.pos.barcode_reader.reset_action_callbacks();
            this.pos_widget.action_bar.destroy_buttons();
        },
    });

    module.ScanProductScreenWidget = module.ScreenWidget.extend({
        template:'ScanProductScreenWidget',
        show: function(){
            this._super();
            var self = this;
            this.pos_widget.action_bar.add_new_button(
                {
                    label: 'help',
                    click: function(){ //TODO Show help popup
                    }
                },{
                    label: 'weight',
                    click: function(){  //TODO Go to ask for weighting screen
                        self.pos.screen_selector.set_current_screen('scale_invite');
                    }
                },{
                    label: 'pay',
                    click: function(){
                        self.pos.screen_selector.set_current_screen('client_payment'); //TODO what stuff ?
                    }
                }
            );
            this.pos.barcode_reader.set_action_callbacks({
                'product': function(ean){
                    var success = self.pos.barcode_reader.scan_product_callback(ean);
                    if(success){
                        self.proxy.scan_item_success();
                    }else{
                        self.proxy.scan_item_error_unrecognized();
                    }
                },
                'cashier': function(ean){
                    //TODO 'switch to cashier mode'
                    self.proxy.cashier_mode_activated();
                },
                'discount': function(ean){
                    // TODO : handle the discount
                },
            });
        },
    });
    
    module.SearchProductScreenWidget = module.ScreenWidget.extend({
        template:'SearchProductScreenWidget',
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
            var self = this;
            this.pos_widget.orderView.setNumpadState(this.pos_widget.numpadView.state);
            this.pos_widget.action_bar.add_new_button(
                {
                    label: 'help',
                    click: function(){ //TODO Show help popup
                    }
                },{
                    label: 'weight',
                    click: function(){  //TODO Go to ask for weighting screen
                    }
                },{
                    label: 'pay',
                    click: function(){
                        self.pos.screen_selector.set_current_screen('payment'); //TODO what stuff ?
                    }
                }
            );
            this.pos.barcode_reader.set_action_callbacks({
                'product': function(ean){
                    var success = self.pos.barcode_reader.scan_product_callback(ean);
                    if(success){
                        self.proxy.scan_item_success();
                    }else{
                        self.proxy.scan_item_error_unrecognized();
                    }
                },
                'cashier': function(ean){
                    //TODO 'switch to cashier mode'
                    self.proxy.cashier_mode_activated();
                },
                'discount': function(ean){
                    // TODO : handle the discount
                },
            });
        },
        hide: function(){
            this._super();
            this.pos_widget.orderView.setNumpadState(null);
            this.pos_widget.payment_screen.setNumpadState(null);
        },

    });

    module.ReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'ReceiptScreenWidget',
        init: function(parent, options) {
            this._super(parent,options);
            this.model = options.model;
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

    module.PaymentScreenWidget = module.ScreenWidget.extend({
        template_fct: qweb_template('PaymentScreenWidget'),
        init: function(parent, options) {
            this._super(parent,options);
            this.model = options.model;
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

}
