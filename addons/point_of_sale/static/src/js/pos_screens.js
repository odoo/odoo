
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

function openerp_pos_screens(instance, module){ //module is instance.point_of_sale
    var QWeb = instance.web.qweb;

    module.ScreenSelector = instance.web.Class.extend({
        init: function(options){
            this.pos = options.pos;

            this.screen_set = options.screen_set || {};

            this.popup_set = options.popup_set || {};

            this.default_client_screen = options.default_client_screen;
            this.default_cashier_screen = options.default_cashier_screen;

            this.current_popup = null;

            this.current_mode = options.default_mode || 'client';

            this.current_screen = null; 

            for(screen_name in this.screen_set){
                this.screen_set[screen_name].hide();
            }
            
            for(popup_name in this.popup_set){
                this.popup_set[popup_name].hide();
            }

            this.selected_order = this.pos.get('selectedOrder');
            this.selected_order.set_screen_data({
                client_screen: this.default_client_screen,
                cashier_screen: this.default_cashier_screen,
            });

            this.pos.bind('change:selectedOrder', this.load_saved_screen, this);
        },
        add_screen: function(screen_name, screen){
            screen.hide();
            this.screen_set[screen_name] = screen;
            return this;
        },
        show_popup: function(name){
            if(this.current_popup){
                this.close_popup();
            }
            this.current_popup = this.popup_set[name];
            this.current_popup.show();
        },
        close_popup: function(){
            if(this.current_popup){
                this.current_popup.hide();
                this.current_popup = null;
            }
        },
        load_saved_screen:  function(){
            this.close_popup();

            var selectedOrder = this.pos.get('selectedOrder');
            
            if(this.current_mode === 'client'){
                this.set_current_screen(selectedOrder.get_screen_data('client_screen') || this.default_client_screen,null,'refresh');
            }else if(this.current_mode === 'cashier'){
                this.set_current_screen(selectedOrder.get_screen_data('cashier_screen') || this.default_cashier_screen,null,'refresh');
            }
            this.selected_order = selectedOrder;
        },
        set_user_mode: function(user_mode){
            if(user_mode !== this.current_mode){
                this.close_popup();
                this.current_mode = user_mode;
                this.load_saved_screen();
            }
        },
        get_user_mode: function(){
            return this.current_mode;
        },
        set_current_screen: function(screen_name,params,refresh){
            var screen = this.screen_set[screen_name];
            if(!screen){
                console.error("ERROR: set_current_screen("+screen_name+") : screen not found");
            }

            this.close_popup();
            var selectedOrder = this.pos.get('selectedOrder');
            if(this.current_mode === 'client'){
                selectedOrder.set_screen_data('client_screen',screen_name);
                if(params){ 
                    selectedOrder.set_screen_data('client_screen_params',params); 
                }
            }else{
                selectedOrder.set_screen_data('cashier_screen',screen_name);
                if(params){
                    selectedOrder.set_screen_data('cashier_screen_params',params);
                }
            }

            if(screen && (refresh || screen !== this.current_screen)){
                if(this.current_screen){
                    this.current_screen.close();
                    this.current_screen.hide();
                }
                this.current_screen = screen;
                this.current_screen.show();
            }
        },
        get_current_screen_param: function(param){
            var selected_order = this.pos.get('selectedOrder');
            if(this.current_mode === 'client'){
                var params = selected_order.get_screen_data('client_screen_params');
            }else{
                var params = selected_order.get_screen_data('cashier_screen_params');
            }
            if(params){
                return params[param];
            }else{
                return undefined;
            }
        },
        set_default_screen: function(){
            this.set_current_screen(this.current_mode === 'client' ? this.default_client_screen : this.default_cashier_screen);
        },
    });

    module.ScreenWidget = module.PosBaseWidget.extend({

        show_numpad:     true,  
        show_leftpane:   true,

        init: function(parent,options){
            this._super(parent,options);
            this.hidden = false;
        },

        help_button_action: function(){
            this.pos_widget.screen_selector.show_popup('help');
        },

        barcode_product_screen:         'products',     //if defined, this screen will be loaded when a product is scanned
        barcode_product_error_popup:    'error',    //if defined, this popup will be loaded when there's an error in the popup

        // what happens when a product is scanned : 
        // it will add the product to the order and go to barcode_product_screen. Or show barcode_product_error_popup if 
        // there's an error.
        barcode_product_action: function(ean){
            if(this.pos_widget.scan_product(ean)){
                this.pos.proxy.scan_item_success(ean);
                if(this.barcode_product_screen){ 
                    this.pos_widget.screen_selector.set_current_screen(this.barcode_product_screen);
                }
            }else{
                this.pos.proxy.scan_item_error_unrecognized(ean);
                if(this.barcode_product_error_popup && this.pos_widget.screen_selector.get_user_mode() !== 'cashier'){
                    this.pos_widget.screen_selector.show_popup(this.barcode_product_error_popup);
                }
            }
        },
        
        // what happens when a cashier id barcode is scanned.
        // the default behavior is the following : 
        // - if there's a user with a matching ean, put it as the active 'cashier', go to cashier mode, and return true
        // - else : do nothing and return false. You probably want to extend this to show and appropriate error popup... 
        barcode_cashier_action: function(ean){
            var users = this.pos.get('user_list');
            for(var i = 0, len = users.length; i < len; i++){
                if(users[i].ean13 === ean.ean){
                    this.pos.set('cashier',users[i]);
                    this.pos_widget.username.refresh();
                    this.pos.proxy.cashier_mode_activated();
                    this.pos_widget.screen_selector.set_user_mode('cashier');
                    return true;
                }
            }
            this.pos.proxy.scan_item_unrecognized(ean);
            return false;
        },
        
        // what happens when a client id barcode is scanned.
        // the default behavior is the following : 
        // - if there's a user with a matching ean, put it as the active 'client' and return true
        // - else : return false. 
        barcode_client_action: function(ean){
            var users = this.pos.get('user_list');
            for(var i = 0, len = users.length; i < len; i++){
                if(users[i].ean13 === ean.ean){
                    this.pos.get('selectedOrder').set_client(users[i]);
                    this.pos_widget.username.refresh();
                    this.pos.proxy.scan_item_success(ean);
                    return true;
                }
            }
            this.pos.proxy.scan_item_unrecognized(ean);
            return false;
            //TODO start the transaction
        },
        
        // what happens when a discount barcode is scanned : the default behavior
        // is to set the discount on the last order.
        barcode_discount_action: function(ean){
            this.pos.proxy.scan_item_success(ean);
            var last_orderline = this.pos.get('selectedOrder').getLastOrderline();
            if(last_orderline){
                last_orderline.set_discount(ean.value)
            }
        },

        // shows an action bar on the screen. The actionbar is automatically shown when you add a button
        // with add_action_button()
        show_action_bar: function(){
            this.pos_widget.action_bar.show();
            this.$element.css({'bottom':'105px'});
        },

        // hides the action bar. The actionbar is automatically hidden when it is empty
        hide_action_bar: function(){
            this.pos_widget.action_bar.hide();
            this.$element.css({'bottom':'0px'});
        },

        // adds a new button to the action bar. The button definition takes three parameters, all optional :
        // - label: the text below the button
        // - icon:  a small icon that will be shown
        // - click: a callback that will be executed when the button is clicked.
        // the method returns a reference to the button widget, and automatically show the actionbar.
        add_action_button: function(button_def){
            this.show_action_bar();
            return this.pos_widget.action_bar.add_new_button(button_def);
        },

        // this method shows the screen and sets up all the widget related to this screen. Extend this method
        // if you want to alter the behavior of the screen.
        show: function(){
            var self = this;

            this.hidden = false;
            if(this.$element){
                this.$element.show();
            }

            if(this.pos_widget.action_bar.get_button_count() > 0){
                this.show_action_bar();
            }else{
                this.hide_action_bar();
            }
            
            // we add the help button by default. we do this because the buttons are cleared on each refresh so that
            // the button stay local to each screen
            this.pos_widget.left_action_bar.add_new_button({
                    label: 'help',
                    icon: '/point_of_sale/static/src/img/icons/png48/help.png',
                    click: function(){ self.help_button_action(); },
                });

            var self = this;
            var cashier_mode = this.pos_widget.screen_selector.get_user_mode() === 'cashier';

            this.pos_widget.set_numpad_visible(this.show_numpad && cashier_mode);
            this.pos_widget.set_leftpane_visible(this.show_leftpane);
            this.pos_widget.set_left_action_bar_visible(this.show_leftpane && !cashier_mode);
            this.pos_widget.set_cashier_controls_visible(cashier_mode);

            if(cashier_mode && this.pos.use_selfcheckout){
                this.pos_widget.client_button.show();
            }else{
                this.pos_widget.client_button.hide();
            }
            if(cashier_mode){
                this.pos_widget.close_button.show();
            }else{
                this.pos_widget.close_button.hide();
            }
            
            this.pos_widget.username.set_user_mode(this.pos_widget.screen_selector.get_user_mode());

            this.pos.barcode_reader.set_action_callback({
                'cashier': self.barcode_cashier_action ? function(ean){ self.barcode_cashier_action(ean); } : undefined ,
                'product': self.barcode_product_action ? function(ean){ self.barcode_product_action(ean); } : undefined ,
                'client' : self.barcode_client_action ?  function(ean){ self.barcode_client_action(ean);  } : undefined ,
                'discount': self.barcode_discount_action ? function(ean){ self.barcode_discount_action(ean); } : undefined,
            });
        },

        // this method is called when the screen is closed to make place for a new screen. this is a good place
        // to put your cleanup stuff as it is guaranteed that for each show() there is one and only one close()
        close: function(){
            if(this.pos.barcode_reader){
                this.pos.barcode_reader.reset_action_callbacks();
            }
            this.pos_widget.action_bar.destroy_buttons();
            this.pos_widget.left_action_bar.destroy_buttons();
        },

        // this methods hides the screen. It's not a good place to put your cleanup stuff as it is called on the
        // POS initialization.
        hide: function(){
            this.hidden = true;
            if(this.$element){
                this.$element.hide();
            }
        },

        // we need this because some screens re-render themselves when they are hidden
        // (due to some events, or magic, or both...)  we must make sure they remain hidden.
        // the good solution would probably be to make them not re-render themselves when they
        // are hidden. 
        renderElement: function(){
            this._super();
            if(this.hidden){
                if(this.$element){
                    this.$element.hide();
                }
            }
        },
    });

    module.PopUpWidget = module.PosBaseWidget.extend({
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

    module.HelpPopupWidget = module.PopUpWidget.extend({
        template:'HelpPopupWidget',
        show: function(){
            this._super();
            this.pos.proxy.help_needed();
            var self = this;
            
            this.$element.find('.button').off('click').click(function(){
                self.pos_widget.screen_selector.close_popup();
                self.pos.proxy.help_canceled();
            });
        },
    });

    module.ErrorPopupWidget = module.PopUpWidget.extend({
        template:'ErrorPopupWidget',
        show: function(){
            var self = this;
            this._super();
            this.pos.proxy.help_needed();
            this.pos.proxy.scan_item_error_unrecognized();

            this.pos.barcode_reader.save_callbacks();
            this.pos.barcode_reader.reset_action_callbacks();
            this.pos.barcode_reader.set_action_callback({
                'cashier': function(ean){
                    clearInterval(this.intervalID);
                    self.pos.proxy.cashier_mode_activated();
                    self.pos_widget.screen_selector.set_user_mode('cashier');
                },
            });
        },
        close:function(){
            this._super();
            this.pos.proxy.help_canceled();
            this.pos.barcode_reader.restore_callbacks();
        },
    });

    module.ErrorProductNotRecognizedPopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorProductNotRecognizedPopupWidget',
    });

    module.ErrorNoSessionPopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorNoSessionPopupWidget',
    });

    module.ScaleInviteScreenWidget = module.ScreenWidget.extend({
        template:'ScaleInviteScreenWidget',

        next_screen:'scale',
        previous_screen:'products',

        show: function(){
            this._super();
            var self = this;

            self.pos.proxy.weighting_start();

            this.intervalID = setInterval(function(){
                var weight = self.pos.proxy.weighting_read_kg();
                if(weight > 0.001){
                    clearInterval(this.intervalID);
                    self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                }
            },500);

            this.add_action_button({
                    label: 'back',
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){  
                        clearInterval(this.intervalID);
                        self.pos.proxy.weighting_end();
                        self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    }
                });
        },
        close: function(){
            this._super();
            clearInterval(this.intervalID);
        },
    });

    module.ScaleScreenWidget = module.ScreenWidget.extend({
        template:'ScaleScreenWidget',

        next_screen: 'products',
        previous_screen: 'products',

        show: function(){
            this._super();
            this.renderElement();
            var self = this;


            this.add_action_button({
                    label: 'back',
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){
                        self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    }
                });

            this.validate_button = this.add_action_button({
                    label: 'Validate',
                    icon: '/point_of_sale/static/src/img/icons/png48/validate.png',
                    click: function(){
                        self.order_product();
                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                    },
                });
            
            this.pos.proxy.weighting_start();
            this.intervalID = setInterval(function(){
                var weight = self.pos.proxy.weighting_read_kg();
                if(weight != self.weight){
                    self.weight = weight;
                    self.renderElement();
                }
            },200);
        },
        renderElement: function(){
            var self = this;
            this._super();
            this.$('.product-picture').click(function(){
                self.order_product();
                self.pos_widget.screen_selector.set_current_screen(self.next_screen);
            });
        },
        get_product: function(){
            var ss = this.pos_widget.screen_selector;
            if(ss){
                return ss.get_current_screen_param('product');
            }else{
                return undefined;
            }
        },
        order_product: function(){
            var weight = this.pos.proxy.weighting_read_kg();
            this.pos.get('selectedOrder').addProduct(this.get_product(),{ quantity:weight });
        },
        get_product_name: function(){
            var product = this.get_product();
            return (product ? product.get('name') : undefined) || 'Unnamed Product';
        },
        get_product_price: function(){
            var product = this.get_product();
            return (product ? product.get('list_price') : 0) || 0;
        },
        get_product_image: function(){
            var product = this.get_product();
            return product ? product.get('product_image_small') : undefined;
        },
        get_product_weight: function(){
            return this.weight || 0;
        },
        close: function(){
            this._super();
            clearInterval(this.intervalID);
            this.pos.proxy.weighting_end();
        },
    });

    module.ClientPaymentScreenWidget =  module.ScreenWidget.extend({
        template:'ClientPaymentScreenWidget',

        next_screen: 'welcome',
        previous_screen: 'products',

        show: function(){
            this._super();
            var self = this;

            this.pos.proxy.payment_request(this.pos.get('selectedOrder').getDueLeft(),'card','info');    //TODO TOTAL

            this.intervalID = setInterval(function(){
                var payment = self.pos.proxy.is_payment_accepted();
                if(payment === 'payment_accepted'){
                    clearInterval(this.intervalID);

                    var currentOrder = self.pos.get('selectedOrder');
                    
                    //we get the first cashregister marked as self-checkout
                    var selfCheckoutRegisters = [];
                    for(var i = 0; i < this.pos.get('cashRegisters').models.length; i++){
                        var cashregister = this.pos.get('cashRegisters').models[i];
                        if(cashregister.self_checkout_payment_method){
                            selfCheckoutRegisters.push(cashregister);
                        }
                    }

                    var cashregister = selfCheckoutRegisters[0] || this.pos.get('cashRegisters').models[0];
                    currentOrder.addPaymentLine(cashregister);

                    self.pos.push_order(currentOrder.exportAsJSON()).then(function() {
                        currentOrder.destroy();
                        self.pos.proxy.transaction_end();
                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                    });
                }else if(payment === 'payment_rejected'){
                    clearInterval(this.intervalID);
                    //TODO show a tryagain thingie ? 
                }
            },500);

            this.add_action_button({
                    label: 'back',
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){  
                        clearInterval(this.intervalID);
                        self.pos.proxy.payment_canceled();
                        self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    }
                });
        },
        close: function(){
            this._super();
            clearInterval(this.intervalID);
        },
    });

    module.WelcomeScreenWidget = module.ScreenWidget.extend({
        template:'WelcomeScreenWidget',

        next_screen: 'products',

        show_numpad:     false,
        show_leftpane:   false,

        barcode_client_action: function(ean){
            this._super(ean);
            this.pos_widget.screen_selector.set_current_screen(this.next_screen);
        },
        
        show: function(){
            this._super();
            var self = this;
            $('.goodbye-message').css({opacity:1}).show();
            setTimeout(function(){
                console.log('kill');
                $('.goodbye-message').animate({opacity:0},500,'swing',function(){$('.goodbye-message').hide();});
            },3000);
        },
    });
    
    module.ProductScreenWidget = module.ScreenWidget.extend({
        template:'ProductScreenWidget',

        scale_screen: 'scale_invite',
        client_next_screen:  'client_payment',

        show_numpad:     true,
        show_leftpane:   true,

        start: function(){ //FIXME this should work as renderElement... but then the categories aren't properly set. explore why
            var self = this;
            this.product_categories_widget = new module.ProductCategoriesWidget(this,{});
            this.product_categories_widget.replace($('.placeholder-ProductCategoriesWidget'));

            this.product_list_widget = new module.ProductListWidget(this,{
                click_product_action: function(product){
                    if(product.get('to_weight') && self.pos.use_scale){
                        self.pos_widget.screen_selector.set_current_screen(self.scale_screen, {product: product});
                    }else{
                        self.pos.get('selectedOrder').addProduct(product);
                    }
                },
            });
            this.product_list_widget.replace($('.placeholder-ProductListWidget'));
        },

        show: function(){
            this._super();
            var self = this;

            this.product_categories_widget.reset_category();

            this.pos_widget.order_widget.set_numpad_state(this.pos_widget.numpad.state);
            if(this.pos.use_virtual_keyboard){
                this.pos_widget.onscreen_keyboard.connect();
            }

            if(this.pos_widget.screen_selector.current_mode === 'client'){ 
                this.add_action_button({
                        label: 'pay',
                        icon: '/point_of_sale/static/src/img/icons/png48/go-next.png',
                        click: function(){  
                            self.pos_widget.screen_selector.set_current_screen(self.client_next_screen);
                        }
                    });
            }
        },

        close: function(){
            this._super();
            this.pos_widget.order_widget.set_numpad_state(null);
            this.pos_widget.payment_screen.set_numpad_state(null);
        },

    });

    module.ReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'ReceiptScreenWidget',

        show_numpad:     true,
        show_leftpane:   true,

        init: function(parent, options) {
            this._super(parent,options);
            this.model = options.model;
            this.user = this.pos.get('user');
            this.company = this.pos.get('company');
            this.shop_obj = this.pos.get('shop');
        },
        renderElement: function() {
            this._super();
            this.pos.bind('change:selectedOrder', this.change_selected_order, this);
            this.change_selected_order();
        },
        show: function(){
            this._super();
            var self = this;

            this.add_action_button({
                    label: 'Print',
                    icon: '/point_of_sale/static/src/img/icons/png48/printer.png',
                    click: function(){ self.print(); },
                });

            this.add_action_button({
                    label: 'Next Order',
                    icon: '/point_of_sale/static/src/img/icons/png48/go-next.png',
                    click: function() { self.finishOrder(); },
                });
        },
        print: function() {
            window.print();
        },
        finishOrder: function() {
            this.pos.get('selectedOrder').destroy();
        },
        change_selected_order: function() {
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
            $('.pos-receipt-container', this.$element).html(QWeb.render('PosTicket',{widget:this}));
        },
    });

    module.PaymentScreenWidget = module.ScreenWidget.extend({
        template: 'PaymentScreenWidget',
        back_screen: 'products',
        next_screen: 'receipt',
        init: function(parent, options) {
            this._super(parent,options);
            this.model = options.model;
            this.pos.bind('change:selectedOrder', this.change_selected_order, this);
            this.bindPaymentLineEvents();
            this.bind_orderline_events();
        },
        show: function(){
            this._super();
            var self = this;

            if(this.pos.use_cashbox){
                this.pos.proxy.open_cashbox();
            }

            this.set_numpad_state(this.pos_widget.numpad.state);
            
            this.back_button = this.add_action_button({
                    label: 'Back',
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){  
                        self.pos_widget.screen_selector.set_current_screen(self.back_screen);
                    },
                });
            
            this.validate_button = this.add_action_button({
                    label: 'Validate',
                    icon: '/point_of_sale/static/src/img/icons/png48/validate.png',
                    click: function(){
                        self.validateCurrentOrder();
                    },
                });
        },
        close: function(){
            this._super();
            this.pos_widget.order_widget.set_numpad_state(null);
            this.pos_widget.payment_screen.set_numpad_state(null);
        },
        back: function() {
            this.pos_widget.screen_selector.set_current_screen(self.back_screen);
        },
        validateCurrentOrder: function() {
            var self = this;
            var currentOrder = this.pos.get('selectedOrder');
            if(this.busy){
                return;
            }else{
                this.busy = true;
            }
            this.validate_button.$element.addClass('disabled');

            this.pos.push_order(currentOrder.exportAsJSON()) 
                .then(function() {
                    if(self.pos.use_proxy_printer){
                        self.pos.proxy.print_receipt(currentOrder.export_for_printing());
                        self.pos.get('selectedOrder').destroy();    //finish order and go back to scan screen
                    }else{
                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                    }
                    self.validate_button.$element.removeClass('disabled');
                    self.busy = false;
                });
        },
        bindPaymentLineEvents: function() {
            this.currentPaymentLines = (this.pos.get('selectedOrder')).get('paymentLines');
            this.currentPaymentLines.bind('add', this.addPaymentLine, this);
            this.currentPaymentLines.bind('remove', this.renderElement, this);
            this.currentPaymentLines.bind('all', this.updatePaymentSummary, this);
        },
        bind_orderline_events: function() {
            this.currentOrderLines = (this.pos.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('all', this.updatePaymentSummary, this);
        },
        change_selected_order: function() {
            this.currentPaymentLines.unbind();
            this.bindPaymentLineEvents();
            this.currentOrderLines.unbind();
            this.bind_orderline_events();
            this.renderElement();
        },
        addPaymentLine: function(newPaymentLine) {
            var x = new module.PaymentlineWidget(null, {
                    payment_line: newPaymentLine
                });
            x.on_delete.add(_.bind(this.deleteLine, this, x));
            x.appendTo(this.$('#paymentlines'));
        },
        renderElement: function() {
            this._super();
            this.$('#paymentlines').empty();
            this.currentPaymentLines.each(_.bind( function(paymentLine) {
                this.addPaymentLine(paymentLine);
            }, this));
            this.updatePaymentSummary();
        },
        deleteLine: function(lineWidget) {
        	this.currentPaymentLines.remove([lineWidget.payment_line]);
        },
        updatePaymentSummary: function() {
            var currentOrder = this.pos.get('selectedOrder');
            var paidTotal = currentOrder.getPaidTotal();
            var dueTotal = currentOrder.getTotal();
            var remaining = dueTotal > paidTotal ? dueTotal - paidTotal : 0;
            var change = paidTotal > dueTotal ? paidTotal - dueTotal : 0;

            this.$('#payment-due-total').html(dueTotal.toFixed(2));
            this.$('#payment-paid-total').html(paidTotal.toFixed(2));
            this.$('#payment-remaining').html(remaining.toFixed(2));
            this.$('#payment-change').html(change.toFixed(2));
        },
        set_numpad_state: function(numpadState) {
        	if (this.numpadState) {
        		this.numpadState.unbind('set_value', this.set_value);
        		this.numpadState.unbind('change:mode', this.setNumpadMode);
        	}
        	this.numpadState = numpadState;
        	if (this.numpadState) {
        		this.numpadState.bind('set_value', this.set_value, this);
        		this.numpadState.bind('change:mode', this.setNumpadMode, this);
        		this.numpadState.reset();
        		this.setNumpadMode();
        	}
        },
    	setNumpadMode: function() {
    		this.numpadState.set({mode: 'payment'});
    	},
        set_value: function(val) {
        	this.currentPaymentLines.last().set({amount: val});
        },
    });

}
