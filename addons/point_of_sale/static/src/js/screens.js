
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
    var QWeb = instance.web.qweb,
    _t = instance.web._t;

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
                this.current_popup.close();
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
        barcode_product_error_popup:    'error-product',    //if defined, this popup will be loaded when there's an error in the popup

        hotkeys_handlers: {},

        // what happens when a product is scanned : 
        // it will add the product to the order and go to barcode_product_screen. Or show barcode_product_error_popup if 
        // there's an error.
        barcode_product_action: function(code){
            var self = this;
            if(self.pos.scan_product(code)){
                self.pos.proxy.scan_item_success(code);
                if(self.barcode_product_screen){ 
                    self.pos_widget.screen_selector.set_current_screen(self.barcode_product_screen);
                }
            }else{
                self.pos.proxy.scan_item_error_unrecognized(code);
                if(self.barcode_product_error_popup && self.pos_widget.screen_selector.get_user_mode() !== 'cashier'){
                    self.pos_widget.screen_selector.show_popup(self.barcode_product_error_popup);
                }
            }
        },

        // what happens when a cashier id barcode is scanned.
        // the default behavior is the following : 
        // - if there's a user with a matching ean, put it as the active 'cashier', go to cashier mode, and return true
        // - else : do nothing and return false. You probably want to extend this to show and appropriate error popup... 
        barcode_cashier_action: function(code){
            var users = this.pos.users;
            for(var i = 0, len = users.length; i < len; i++){
                if(users[i].ean13 === code.code){
                    this.pos.cashier = users[i];
                    this.pos_widget.username.refresh();
                    this.pos.proxy.cashier_mode_activated();
                    this.pos_widget.screen_selector.set_user_mode('cashier');
                    return true;
                }
            }
            this.pos.proxy.scan_item_error_unrecognized(code);
            return false;
        },
        
        // what happens when a client id barcode is scanned.
        // the default behavior is the following : 
        // - if there's a user with a matching ean, put it as the active 'client' and return true
        // - else : return false. 
        barcode_client_action: function(code){
            var partners = this.pos.partners;
            for(var i = 0, len = partners.length; i < len; i++){
                if(partners[i].ean13 === code.code){
                    this.pos.get('selectedOrder').set_client(partners[i]);
                    this.pos_widget.username.refresh();
                    this.pos.proxy.scan_item_success(code);
                    return true;
                }
            }
            this.pos.proxy.scan_item_error_unrecognized(code);
            return false;
            //TODO start the transaction
        },
        
        // what happens when a discount barcode is scanned : the default behavior
        // is to set the discount on the last order.
        barcode_discount_action: function(code){
            this.pos.proxy.scan_item_success(code);
            var last_orderline = this.pos.get('selectedOrder').getLastOrderline();
            if(last_orderline){
                last_orderline.set_discount(code.value)
            }
        },

        // shows an action bar on the screen. The actionbar is automatically shown when you add a button
        // with add_action_button()
        show_action_bar: function(){
            this.pos_widget.action_bar.show();
        },

        // hides the action bar. The actionbar is automatically hidden when it is empty
        hide_action_bar: function(){
            this.pos_widget.action_bar.hide();
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
            if(this.$el){
                this.$el.removeClass('oe_hidden');
            }

            if(this.pos_widget.action_bar.get_button_count() > 0){
                this.show_action_bar();
            }else{
                this.hide_action_bar();
            }
            
            // we add the help button by default. we do this because the buttons are cleared on each refresh so that
            // the button stay local to each screen
            this.pos_widget.left_action_bar.add_new_button({
                    label: _t('Help'),
                    icon: '/point_of_sale/static/src/img/icons/png48/help.png',
                    click: function(){ self.help_button_action(); },
                });

            var self = this;
            this.cashier_mode = this.pos_widget.screen_selector.get_user_mode() === 'cashier';

            this.pos_widget.set_numpad_visible(this.show_numpad && this.cashier_mode);
            this.pos_widget.set_leftpane_visible(this.show_leftpane);
            this.pos_widget.set_left_action_bar_visible(this.show_leftpane && !this.cashier_mode);
            this.pos_widget.set_cashier_controls_visible(this.cashier_mode);

            if(this.cashier_mode && this.pos.config.iface_self_checkout){
                this.pos_widget.client_button.show();
            }else{
                this.pos_widget.client_button.hide();
            }
            if(this.cashier_mode){
                this.pos_widget.close_button.show();
            }else{
                this.pos_widget.close_button.hide();
            }
            
            this.pos_widget.username.set_user_mode(this.pos_widget.screen_selector.get_user_mode());

            this.pos.barcode_reader.set_action_callback({
                'cashier': self.barcode_cashier_action ? function(code){ self.barcode_cashier_action(code); } : undefined ,
                'product': self.barcode_product_action ? function(code){ self.barcode_product_action(code); } : undefined ,
                'client' : self.barcode_client_action ?  function(code){ self.barcode_client_action(code);  } : undefined ,
                'discount': self.barcode_discount_action ? function(code){ self.barcode_discount_action(code); } : undefined,
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
            if(this.$el){
                this.$el.addClass('oe_hidden');
            }
        },

        // we need this because some screens re-render themselves when they are hidden
        // (due to some events, or magic, or both...)  we must make sure they remain hidden.
        // the good solution would probably be to make them not re-render themselves when they
        // are hidden. 
        renderElement: function(){
            this._super();
            if(this.hidden){
                if(this.$el){
                    this.$el.addClass('oe_hidden');
                }
            }
        },
    });

    module.PopUpWidget = module.PosBaseWidget.extend({
        show: function(){
            if(this.$el){
                this.$el.removeClass('oe_hidden');
            }
        },
        /* called before hide, when a popup is closed */
        close: function(){
        },
        /* hides the popup. keep in mind that this is called in the initialization pass of the 
         * pos instantiation, so you don't want to do anything fancy in here */
        hide: function(){
            if(this.$el){
                this.$el.addClass('oe_hidden');
            }
        },
    });

    module.HelpPopupWidget = module.PopUpWidget.extend({
        template:'HelpPopupWidget',
        show: function(){
            this._super();
            this.pos.proxy.help_needed();
            var self = this;
            
            this.$el.find('.button').off('click').click(function(){
                self.pos_widget.screen_selector.close_popup();
            });
        },
        close:function(){
            this.pos.proxy.help_canceled();
        },
    });

    module.ChooseReceiptPopupWidget = module.PopUpWidget.extend({
        template:'ChooseReceiptPopupWidget',
        show: function(){
            this._super();
            this.renderElement();
            var self = this;
            var currentOrder = self.pos.get('selectedOrder');
            
            this.$('.button.receipt').off('click').click(function(){
                currentOrder.set_receipt_type('receipt');
                self.pos_widget.screen_selector.set_current_screen('products');
            });

            this.$('.button.invoice').off('click').click(function(){
                currentOrder.set_receipt_type('invoice');
                self.pos_widget.screen_selector.set_current_screen('products');
            });
        },
        get_client_name: function(){
            var client = this.pos.get('selectedOrder').get_client();
            if( client ){
                return client.name;
            }else{
                return '';
            }
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
                'cashier': function(code){
                    clearInterval(this.intervalID);
                    self.pos.proxy.cashier_mode_activated();
                    self.pos_widget.screen_selector.set_user_mode('cashier');
                },
            });
            this.$('.footer .button').off('click').click(function(){
                self.pos_widget.screen_selector.close_popup();
            });
        },
        close:function(){
            this._super();
            this.pos.proxy.help_canceled();
            this.pos.barcode_reader.restore_callbacks();
        },
    });

    module.ProductErrorPopupWidget = module.ErrorPopupWidget.extend({
        template:'ProductErrorPopupWidget',
    });

    module.ErrorSessionPopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorSessionPopupWidget',
    });

    module.ErrorNegativePricePopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorNegativePricePopupWidget',
    });

    module.ErrorNoClientPopupWidget = module.ErrorPopupWidget.extend({
        template: 'ErrorNoClientPopupWidget',
    });

    module.ErrorInvoiceTransferPopupWidget = module.ErrorPopupWidget.extend({
        template: 'ErrorInvoiceTransferPopupWidget',
    });
                
    module.ScaleInviteScreenWidget = module.ScreenWidget.extend({
        template:'ScaleInviteScreenWidget',

        next_screen:'scale',
        previous_screen:'products',

        show: function(){
            this._super();
            var self = this;
            var queue = this.pos.proxy_queue;

            queue.schedule(function(){
                return self.pos.proxy.weighting_start();
            },{ important: true });
            
            queue.schedule(function(){
                return self.pos.proxy.weighting_read_kg().then(function(weight){
                    if(weight > 0.001){
                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                    }
                });
            },{duration: 100, repeat: true});

            this.add_action_button({
                    label: _t('Back'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){  
                        self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    }
                });
        },
        close: function(){
            this._super();
            var self = this;
            this.pos.proxy_queue.clear();
            this.pos.proxy_queue.schedule(function(){
                return self.pos.proxy.weighting_end();
            },{ important: true });
        },
    });

    module.ScaleScreenWidget = module.ScreenWidget.extend({
        template:'ScaleScreenWidget',

        next_screen: 'products',
        previous_screen: 'products',

        show: function(){
            this._super();
            var self = this;
            var queue = this.pos.proxy_queue;

            this.set_weight(0);
            this.renderElement();

            this.hotkey_handler = function(event){
                if(event.which === 13){
                    self.order_product();
                    self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                }else if(event.which === 27){
                    self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                }
            };

            $('body').on('keyup',this.hotkey_handler);

            this.add_action_button({
                    label: _t('Back'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){
                        self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    }
                });

            this.validate_button = this.add_action_button({
                    label: _t('Validate'),
                    icon: '/point_of_sale/static/src/img/icons/png48/validate.png',
                    click: function(){
                        self.order_product();
                        self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                    },
                });
            
            queue.schedule(function(){
                return self.pos.proxy.weighting_start()
            },{ important: true });
            
            queue.schedule(function(){
                return self.pos.proxy.weighting_read_kg().then(function(weight){
                    self.set_weight(weight);
                });
            },{duration:50, repeat: true});

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
            this.pos.get('selectedOrder').addProduct(this.get_product(),{ quantity: this.weight });
        },
        get_product_name: function(){
            var product = this.get_product();
            return (product ? product.name : undefined) || 'Unnamed Product';
        },
        get_product_price: function(){
            var product = this.get_product();
            return (product ? product.price : 0) || 0;
        },
        set_weight: function(weight){
            this.weight = weight;
            this.$('.js-weight').text(this.get_product_weight_string());
        },
        get_product_weight_string: function(){
            return (this.weight || 0).toFixed(3) + ' Kg';
        },
        get_product_image_url: function(){
            var product = this.get_product();
            if(product){
                return window.location.origin + '/web/binary/image?model=product.product&field=image_medium&id='+product.id;
            }else{
                return "";
            }
        },
        close: function(){
            var self = this;
            this._super();
            $('body').off('keyup',this.hotkey_handler);

            this.pos.proxy_queue.clear();
            this.pos.proxy_queue.schedule(function(){
                self.pos.proxy.weighting_end();
            },{ important: true });
        },
    });


    module.ClientPaymentScreenWidget =  module.ScreenWidget.extend({
        template:'ClientPaymentScreenWidget',

        next_screen: 'welcome',
        previous_screen: 'products',

        show: function(){
            this._super();
            var self = this;
           
            this.queue = new module.JobQueue();
            this.canceled = false;
            this.paid     = false;

            // initiates the connection to the payment terminal and starts the update requests
            this.start = function(){
                var def = new $.Deferred();
                self.pos.proxy.payment_request(self.pos.get('selectedOrder').getDueLeft())
                    .done(function(ack){
                        if(ack === 'ok'){
                            self.queue.schedule(self.update);
                        }else if(ack.indexOf('error') === 0){
                            console.error('cannot make payment. TODO');
                        }else{
                            console.error('unknown payment request return value:',ack);
                        }
                        def.resolve();
                    });
                return def;
            };
            
            // gets updated status from the payment terminal and performs the appropriate consequences
            this.update = function(){
                var def = new $.Deferred();
                if(self.canceled){
                    return def.resolve();
                }
                self.pos.proxy.payment_status()
                    .done(function(status){
                        if(status.status === 'paid'){

                            var currentOrder = self.pos.get('selectedOrder');
                            
                            //we get the first cashregister marked as self-checkout
                            var selfCheckoutRegisters = [];
                            for(var i = 0; i < self.pos.cashregisters.length; i++){
                                var cashregister = self.pos.cashregisters[i];
                                if(cashregister.self_checkout_payment_method){
                                    selfCheckoutRegisters.push(cashregister);
                                }
                            }

                            var cashregister = selfCheckoutRegisters[0] || self.pos.cashregisters[0];
                            currentOrder.addPaymentline(cashregister);
                            self.pos.push_order(currentOrder)
                            currentOrder.destroy();
                            self.pos.proxy.transaction_end();
                            self.pos_widget.screen_selector.set_current_screen(self.next_screen);
                            self.paid = true;
                        }else if(status.status.indexOf('error') === 0){
                            console.error('error in payment request. TODO');
                        }else if(status.status === 'waiting'){
                            self.queue.schedule(self.update,200);
                        }else{
                            console.error('unknown status value:',status.status);
                        }
                        def.resolve();
                    });
                return def;
            }
            
            // cancels a payment.
            this.cancel = function(){
                if(!self.paid && !self.canceled){
                    self.canceled = true;
                    self.pos.proxy.payment_cancel();
                    self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    self.queue.clear();
                }
                return (new $.Deferred()).resolve();
            }
            
            if(this.pos.get('selectedOrder').getDueLeft() <= 0){
                this.pos_widget.screen_selector.show_popup('error-negative-price');
            }else{
                this.queue.schedule(this.start);
            }

            this.add_action_button({
                    label: _t('Back'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){  
                       self.queue.schedule(self.cancel);
                       self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
                    }
                });
        },
        close: function(){
            if(this.queue){
                this.queue.schedule(this.cancel);
            }
            //TODO CANCEL
            this._super();
        },
    });

    module.WelcomeScreenWidget = module.ScreenWidget.extend({
        template:'WelcomeScreenWidget',

        next_screen: 'products',

        show_numpad:     false,
        show_leftpane:   false,
        start: function(){
            this._super();
            $('.goodbye-message').click(function(){
                $(this).addClass('oe_hidden');
            });
        },

        barcode_product_action: function(code){
            this.pos.proxy.transaction_start();
            this._super(code);
        },

        barcode_client_action: function(code){
            this.pos.proxy.transaction_start();
            this._super(code);
            $('.goodbye-message').addClass('oe_hidden');
            this.pos_widget.screen_selector.show_popup('choose-receipt');
        },
        
        show: function(){
            this._super();
            var self = this;

            this.add_action_button({
                    label: _t('Help'),
                    icon: '/point_of_sale/static/src/img/icons/png48/help.png',
                    click: function(){ 
                        $('.goodbye-message').css({opacity:1}).addClass('oe_hidden');
                        self.help_button_action();
                    },
                });

            $('.goodbye-message').css({opacity:1}).removeClass('oe_hidden');
            setTimeout(function(){
                $('.goodbye-message').animate({opacity:0},500,'swing',function(){$('.goodbye-message').addClass('oe_hidden');});
            },5000);
        },
    });
    
    module.ProductScreenWidget = module.ScreenWidget.extend({
        template:'ProductScreenWidget',

        scale_screen: 'scale',
        client_scale_screen : 'scale_invite',
        client_next_screen:  'client_payment',

        show_numpad:     true,
        show_leftpane:   true,

        start: function(){ //FIXME this should work as renderElement... but then the categories aren't properly set. explore why
            var self = this;

            this.product_list_widget = new module.ProductListWidget(this,{
                click_product_action: function(product){
                    if(product.to_weight && self.pos.config.iface_electronic_scale){
                        self.pos_widget.screen_selector.set_current_screen( self.cashier_mode ? self.scale_screen : self.client_scale_screen, {product: product});
                    }else{
                        self.pos.get('selectedOrder').addProduct(product);
                    }
                },
                product_list: this.pos.db.get_product_by_category(0)
            });
            this.product_list_widget.replace($('.placeholder-ProductListWidget'));

            this.product_categories_widget = new module.ProductCategoriesWidget(this,{
                product_list_widget: this.product_list_widget,
            });
            this.product_categories_widget.replace($('.placeholder-ProductCategoriesWidget'));
        },

        show: function(){
            this._super();
            var self = this;

            this.product_categories_widget.reset_category();

            this.pos_widget.order_widget.set_editable(true);

            if(this.pos_widget.screen_selector.current_mode === 'client'){ 
                this.add_action_button({
                        label: _t('Pay'),
                        icon: '/point_of_sale/static/src/img/icons/png48/go-next.png',
                        click: function(){  
                            self.pos_widget.screen_selector.set_current_screen(self.client_next_screen);
                        }
                    });
            }
        },

        close: function(){
            this._super();

            this.pos_widget.order_widget.set_editable(false);

            if(this.pos.config.iface_vkeyboard && this.pos_widget.onscreen_keyboard){
                this.pos_widget.onscreen_keyboard.hide();
            }
        },
    });

    module.ReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'ReceiptScreenWidget',

        show_numpad:     true,
        show_leftpane:   true,

        show: function(){
            this._super();
            var self = this;

            var print_button = this.add_action_button({
                    label: _t('Print'),
                    icon: '/point_of_sale/static/src/img/icons/png48/printer.png',
                    click: function(){ self.print(); },
                });

            var finish_button = this.add_action_button({
                    label: _t('Next Order'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-next.png',
                    click: function() { self.finishOrder(); },
                });

            this.refresh();
            this.print();

            //
            // The problem is that in chrome the print() is asynchronous and doesn't
            // execute until all rpc are finished. So it conflicts with the rpc used
            // to send the orders to the backend, and the user is able to go to the next 
            // screen before the printing dialog is opened. The problem is that what's 
            // printed is whatever is in the page when the dialog is opened and not when it's called,
            // and so you end up printing the product list instead of the receipt... 
            //
            // Fixing this would need a re-architecturing
            // of the code to postpone sending of orders after printing.
            //
            // But since the print dialog also blocks the other asynchronous calls, the
            // button enabling in the setTimeout() is blocked until the printing dialog is 
            // closed. But the timeout has to be big enough or else it doesn't work
            // 2 seconds is the same as the default timeout for sending orders and so the dialog
            // should have appeared before the timeout... so yeah that's not ultra reliable. 

            finish_button.set_disabled(true);   
            setTimeout(function(){
                finish_button.set_disabled(false);
            }, 2000);
        },
        print: function() {
            window.print();
        },
        finishOrder: function() {
            this.pos.get('selectedOrder').destroy();
        },
        refresh: function() {
            var order = this.pos.get('selectedOrder');
            $('.pos-receipt-container', this.$el).html(QWeb.render('PosTicket',{
                    widget:this,
                    order: order,
                    orderlines: order.get('orderLines').models,
                    paymentlines: order.get('paymentLines').models,
                }));
        },
        close: function(){
            this._super();
        }
    });

    module.PaymentScreenWidget = module.ScreenWidget.extend({
        template: 'PaymentScreenWidget',
        back_screen: 'products',
        next_screen: 'receipt',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);

            this.pos.bind('change:selectedOrder',function(){
                    this.bind_events();
                    this.renderElement();
                },this);

            this.bind_events();

            this.line_delete_handler = function(event){
                var node = this;
                while(node && !node.classList.contains('paymentline')){
                    node = node.parentNode;
                }
                if(node){
                    self.pos.get('selectedOrder').removePaymentline(node.line)   
                }
                event.stopPropagation();
            };

            this.line_change_handler = function(event){
                var node = this;
                while(node && !node.classList.contains('paymentline')){
                    node = node.parentNode;
                }
                if(node){
                    node.line.set_amount(this.value);
                }
                
            };

            this.line_click_handler = function(event){
                var node = this;
                while(node && !node.classList.contains('paymentline')){
                    node = node.parentNode;
                }
                if(node){
                    self.pos.get('selectedOrder').selectPaymentline(node.line);
                }
            };

            this.hotkey_handler = function(event){
                if(event.which === 13){
                    self.validate_order();
                }else if(event.which === 27){
                    self.back();
                }
            };

        },
        show: function(){
            this._super();
            var self = this;
            
            this.enable_numpad();
            this.focus_selected_line();
            
            document.body.addEventListener('keyup', this.hotkey_handler);
            


            this.add_action_button({
                    label: _t('Back'),
                    icon: '/point_of_sale/static/src/img/icons/png48/go-previous.png',
                    click: function(){  
                        self.back();
                    },
                });

            this.add_action_button({
                    label: _t('Validate'),
                    name: 'validation',
                    icon: '/point_of_sale/static/src/img/icons/png48/validate.png',
                    click: function(){
                        self.validate_order();
                    },
                });
           
            if( this.pos.config.iface_invoicing ){
                this.add_action_button({
                        label: 'Invoice',
                        name: 'invoice',
                        icon: '/point_of_sale/static/src/img/icons/png48/invoice.png',
                        click: function(){
                            self.validate_order({invoice: true});
                        },
                    });
            }

            if( this.pos.config.iface_cashdrawer ){
                this.add_action_button({
                        label: _t('Cash'),
                        name: 'cashbox',
                        icon: '/point_of_sale/static/src/img/open-cashbox.png',
                        click: function(){
                            self.pos.proxy.open_cashbox();
                        },
                    });
            }

            this.update_payment_summary();

        },
        close: function(){
            this._super();
            this.disable_numpad();
            document.body.removeEventListener('keyup',this.hotkey_handler);
        },
        remove_empty_lines: function(){
            var order = this.pos.get('selectedOrder');
            var lines = order.get('paymentLines').models.slice(0);
            for(var i = 0; i < lines.length; i++){ 
                var line = lines[i];
                if(line.get_amount() === 0){
                    order.removePaymentline(line);
                }
            }
        },
        back: function() {
            this.remove_empty_lines();
            this.pos_widget.screen_selector.set_current_screen(this.back_screen);
        },
        bind_events: function() {
            if(this.old_order){
                this.old_order.unbind(null,null,this);
            }
            var order = this.pos.get('selectedOrder');
                order.bind('change:selected_paymentline',this.focus_selected_line,this);

            this.old_order = order;

            if(this.old_paymentlines){
                this.old_paymentlines.unbind(null,null,this);
            }
            var paymentlines = order.get('paymentLines');
                paymentlines.bind('add', this.add_paymentline, this);
                paymentlines.bind('change:selected', this.rerender_paymentline, this);
                paymentlines.bind('change:amount', function(line){
                        if(!line.selected && line.node){
                            line.node.value = line.amount.toFixed(2);
                        }
                        this.update_payment_summary();
                    },this);
                paymentlines.bind('remove', this.remove_paymentline, this);
                paymentlines.bind('all', this.update_payment_summary, this);

            this.old_paymentlines = paymentlines;

            if(this.old_orderlines){
                this.old_orderlines.unbind(null,null,this);
            }
            var orderlines = order.get('orderLines');
                orderlines.bind('all', this.update_payment_summary, this);

            this.old_orderlines = orderlines;
        },
        focus_selected_line: function(){
            var line = this.pos.get('selectedOrder').selected_paymentline;
            if(line){
                var input = line.node.querySelector('input');
                if(!input){
                    return;
                }
                var value = input.value;
                input.focus();

                if(this.numpad_state){
                    this.numpad_state.reset();
                }

                if(Number(value) === 0){
                    input.value = '';
                }else{
                    input.value = value;
                    input.select();
                }
            }
        },
        add_paymentline: function(line) {
            var list_container = this.el.querySelector('.payment-lines');
                list_container.appendChild(this.render_paymentline(line));
            
            if(this.numpad_state){
                this.numpad_state.reset();
            }
        },
        render_paymentline: function(line){
            var el_html  = openerp.qweb.render('Paymentline',{widget: this, line: line});
                el_html  = _.str.trim(el_html);

            var el_node  = document.createElement('tbody');
                el_node.innerHTML = el_html;
                el_node = el_node.childNodes[0];
                el_node.line = line;
                el_node.querySelector('.paymentline-delete')
                    .addEventListener('click', this.line_delete_handler);
                el_node.addEventListener('click', this.line_click_handler);
                el_node.querySelector('input')
                    .addEventListener('keyup', this.line_change_handler);

            line.node = el_node;

            return el_node;
        },
        rerender_paymentline: function(line){
            var old_node = line.node;
            var new_node = this.render_paymentline(line);
            
            old_node.parentNode.replaceChild(new_node,old_node);
        },
        remove_paymentline: function(line){
            line.node.parentNode.removeChild(line.node);
            line.node = undefined;
        },
        renderElement: function(){
            this._super();

            var paymentlines   = this.pos.get('selectedOrder').get('paymentLines').models;
            var list_container = this.el.querySelector('.payment-lines');

            for(var i = 0; i < paymentlines.length; i++){
                list_container.appendChild(this.render_paymentline(paymentlines[i]));
            }
            
            this.update_payment_summary();
        },
        update_payment_summary: function() {
            var currentOrder = this.pos.get('selectedOrder');
            var paidTotal = currentOrder.getPaidTotal();
            var dueTotal = currentOrder.getTotalTaxIncluded();
            var remaining = dueTotal > paidTotal ? dueTotal - paidTotal : 0;
            var change = paidTotal > dueTotal ? paidTotal - dueTotal : 0;

            this.$('.payment-due-total').html(this.format_currency(dueTotal));
            this.$('.payment-paid-total').html(this.format_currency(paidTotal));
            this.$('.payment-remaining').html(this.format_currency(remaining));
            this.$('.payment-change').html(this.format_currency(change));
            if(currentOrder.selected_orderline === undefined){
                remaining = 1;  // What is this ? 
            }
                
            if(this.pos_widget.action_bar){
                this.pos_widget.action_bar.set_button_disabled('validation', !this.is_paid());
                this.pos_widget.action_bar.set_button_disabled('invoice', !this.is_paid());
            }
        },
        is_paid: function(){
            var currentOrder = this.pos.get('selectedOrder');
            return (currentOrder.getTotalTaxIncluded() >= 0.000001 
                   && currentOrder.getPaidTotal() + 0.000001 >= currentOrder.getTotalTaxIncluded());

        },
        validate_order: function(options) {
            var self = this;
            options = options || {};

            var currentOrder = this.pos.get('selectedOrder');

            if(!this.is_paid()){
                return;
            }

            if(    this.pos.config.iface_cashdrawer 
                && this.pos.get('selectedOrder').get('paymentLines').find( function(pl){ 
                           return pl.cashregister.journal.type === 'cash'; 
                   })){
                    this.pos.proxy.open_cashbox();
            }

            if(options.invoice){
                // deactivate the validation button while we try to send the order
                this.pos_widget.action_bar.set_button_disabled('validation',true);
                this.pos_widget.action_bar.set_button_disabled('invoice',true);

                var invoiced = this.pos.push_and_invoice_order(currentOrder);

                invoiced.fail(function(error){
                    if(error === 'error-no-client'){
                        self.pos_widget.screen_selector.show_popup('error-no-client');
                    }else{
                        self.pos_widget.screen_selector.show_popup('error-invoice-transfer');
                    }
                    self.pos_widget.action_bar.set_button_disabled('validation',false);
                    self.pos_widget.action_bar.set_button_disabled('invoice',false);
                });

                invoiced.done(function(){
                    self.pos_widget.action_bar.set_button_disabled('validation',false);
                    self.pos_widget.action_bar.set_button_disabled('invoice',false);
                    self.pos.get('selectedOrder').destroy();
                });

            }else{
                this.pos.push_order(currentOrder) 
                if(this.pos.config.iface_print_via_proxy){
                    this.pos.proxy.print_receipt(currentOrder.export_for_printing());
                    this.pos.get('selectedOrder').destroy();    //finish order and go back to scan screen
                }else{
                    this.pos_widget.screen_selector.set_current_screen(this.next_screen);
                }
            }

            // hide onscreen (iOS) keyboard 
            setTimeout(function(){
                document.activeElement.blur();
                $("input").blur();
            },250);
        },
        enable_numpad: function(){
            this.disable_numpad();  //ensure we don't register the callbacks twice
            this.numpad_state = this.pos_widget.numpad.state;
            if(this.numpad_state){
                this.numpad_state.reset();
                this.numpad_state.changeMode('payment');
                this.numpad_state.bind('set_value',   this.set_value, this);
                this.numpad_state.bind('change:mode', this.set_mode_back_to_payment, this);
            }
                    
        },
        disable_numpad: function(){
            if(this.numpad_state){
                this.numpad_state.unbind('set_value',  this.set_value);
                this.numpad_state.unbind('change:mode',this.set_mode_back_to_payment);
            }
        },
    	set_mode_back_to_payment: function() {
    		this.numpad_state.set({mode: 'payment'});
    	},
        set_value: function(val) {
            var selected_line =this.pos.get('selectedOrder').selected_paymentline;
            if(selected_line){
                selected_line.set_amount(val);
                selected_line.node.querySelector('input').value = selected_line.amount.toFixed(2);
            }
        },
    });
}
