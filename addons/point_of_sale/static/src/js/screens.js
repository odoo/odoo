
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

    var round_pr = instance.web.round_precision

    module.ScreenSelector = instance.web.Class.extend({
        init: function(options){
            this.pos = options.pos;

            this.screen_set = options.screen_set || {};

            this.popup_set = options.popup_set || {};

            this.default_screen = options.default_screen;

            this.current_popup = null;

            this.current_mode = options.default_mode || 'cashier';

            this.current_screen = null; 

            for(screen_name in this.screen_set){
                this.screen_set[screen_name].hide();
            }
            
            for(popup_name in this.popup_set){
                this.popup_set[popup_name].hide();
            }

            this.pos.get('selectedOrder').set_screen_data({
                'screen': this.default_screen,
            });

            this.pos.bind('change:selectedOrder', this.load_saved_screen, this);
        },
        add_screen: function(screen_name, screen){
            screen.hide();
            this.screen_set[screen_name] = screen;
            return this;
        },
        show_popup: function(name,options){
            if(this.current_popup){
                this.close_popup();
            }
            this.current_popup = this.popup_set[name];
            this.current_popup.show(options);
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
            // FIXME : this changing screen behaviour is sometimes confusing ... 
            this.set_current_screen(selectedOrder.get_screen_data('screen') || this.default_screen,null,'refresh');
            //this.set_current_screen(this.default_screen,null,'refresh');
            
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

            var order = this.pos.get('selectedOrder');
            var old_screen_name = order.get_screen_data('screen');

            order.set_screen_data('screen',screen_name);

            if(params){
                order.set_screen_data('params',params);
            }

            if( screen_name !== old_screen_name ){
                order.set_screen_data('previous-screen',old_screen_name);
            }

            if ( refresh || screen !== this.current_screen){
                if(this.current_screen){
                    this.current_screen.close();
                    this.current_screen.hide();
                }
                this.current_screen = screen;
                this.current_screen.show();
            }
        },
        get_current_screen: function(){
            return this.pos.get('selectedOrder').get_screen_data('screen') || this.default_screen;
        },
        back: function(){
            var previous = this.pos.get('selectedOrder').get_screen_data('previous-screen');
            if(previous){
                this.set_current_screen(previous);
            }
        },
        get_current_screen_param: function(param){
            var params = this.pos.get('selectedOrder').get_screen_data('params');
            return params ? params[param] : undefined;
        },
        set_default_screen: function(){
            this.set_current_screen(this.default_screen);
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

        hotkeys_handlers: {},

        // what happens when a product is scanned : 
        // it will add the product to the order and go to barcode_product_screen. 
        barcode_product_action: function(code){
            var self = this;
            if(self.pos.scan_product(code)){
                if(self.barcode_product_screen){ 
                    self.pos_widget.screen_selector.set_current_screen(self.barcode_product_screen);
                }
            }else{
                self.pos_widget.screen_selector.show_popup('error-barcode',code.code);
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
                    return true;
                }
            }
            this.pos_widget.screen_selector.show_popup('error-barcode',code.code);
            return false;
        },
        
        // what happens when a client id barcode is scanned.
        // the default behavior is the following : 
        // - if there's a user with a matching ean, put it as the active 'client' and return true
        // - else : return false. 
        barcode_client_action: function(code){
            var partner = this.pos.db.get_partner_by_ean13(code.code);
            if(partner){
                this.pos.get('selectedOrder').set_client(partner);
                this.pos_widget.username.refresh();
                return true;
            }
            this.pos_widget.screen_selector.show_popup('error-barcode',code.code);
            return false;
        },
        
        // what happens when a discount barcode is scanned : the default behavior
        // is to set the discount on the last order.
        barcode_discount_action: function(code){
            var last_orderline = this.pos.get('selectedOrder').getLastOrderline();
            if(last_orderline){
                last_orderline.set_discount(code.value)
            }
        },
        // What happens when an invalid barcode is scanned : shows an error popup.
        barcode_error_action: function(code){
            this.pos_widget.screen_selector.show_popup('error-barcode',code.code);
        },

        // this method shows the screen and sets up all the widget related to this screen. Extend this method
        // if you want to alter the behavior of the screen.
        show: function(){
            var self = this;

            this.hidden = false;
            if(this.$el){
                this.$el.removeClass('oe_hidden');
            }

            var self = this;

            this.pos_widget.set_numpad_visible(this.show_numpad);
            this.pos_widget.set_leftpane_visible(this.show_leftpane);

            this.pos_widget.username.set_user_mode(this.pos_widget.screen_selector.get_user_mode());

            this.pos.barcode_reader.set_action_callback({
                'cashier': self.barcode_cashier_action ? function(code){ self.barcode_cashier_action(code); } : undefined ,
                'product': self.barcode_product_action ? function(code){ self.barcode_product_action(code); } : undefined ,
                'client' : self.barcode_client_action ?  function(code){ self.barcode_client_action(code);  } : undefined ,
                'discount': self.barcode_discount_action ? function(code){ self.barcode_discount_action(code); } : undefined,
                'error'   : self.barcode_error_action ?  function(code){ self.barcode_error_action(code);   } : undefined,
            });
        },

        // this method is called when the screen is closed to make place for a new screen. this is a good place
        // to put your cleanup stuff as it is guaranteed that for each show() there is one and only one close()
        close: function(){
            if(this.pos.barcode_reader){
                this.pos.barcode_reader.reset_action_callbacks();
            }
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


    module.FullscreenPopup = module.PopUpWidget.extend({
        template:'FullscreenPopupWidget',
        show: function(){
            var self = this;
            this._super();
            this.renderElement();
            this.$('.button.fullscreen').off('click').click(function(){
                window.document.body.webkitRequestFullscreen();
                self.pos_widget.screen_selector.close_popup();
            });
            this.$('.button.cancel').off('click').click(function(){
                self.pos_widget.screen_selector.close_popup();
            });
        },
        ismobile: function(){
            return typeof window.orientation !== 'undefined'; 
        }
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
        show: function(text){
            var self = this;
            this._super();

            $('body').append('<audio src="/point_of_sale/static/src/sounds/error.wav" autoplay="true"></audio>');

            if( text ) {
                if ( text.message || text.comment ) {
                    this.$('.message').text(text.message);
                    this.$('.comment').text(text.comment);
                } else {
                    this.$('.message').text(_t('Error'));
                    this.$('.comment').html(text);
                }
            }

            this.pos.barcode_reader.save_callbacks();
            this.pos.barcode_reader.reset_action_callbacks();
            this.$('.footer .button').off('click').click(function(){
                self.pos_widget.screen_selector.close_popup();
            });
        },
        close:function(){
            this._super();
            this.pos.barcode_reader.restore_callbacks();
        },
    });

    module.ErrorTracebackPopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorTracebackPopupWidget',
    });

    module.ErrorSessionPopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorSessionPopupWidget',
    });

    module.ErrorBarcodePopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorBarcodePopupWidget',
        show: function(barcode){
            this._super();
            this.$('.barcode').text(barcode);

        },
    });

    module.ConfirmPopupWidget = module.PopUpWidget.extend({
        template: 'ConfirmPopupWidget',
        show: function(options){
            var self = this;
            this._super();

            this.message = options.message || '';
            this.comment = options.comment || '';
            this.renderElement();
            
            this.$('.button.cancel').click(function(){
                self.pos_widget.screen_selector.close_popup();
                if( options.cancel ){
                    options.cancel.call(self);
                }
            });

            this.$('.button.confirm').click(function(){
                self.pos_widget.screen_selector.close_popup();
                if( options.confirm ){
                    options.confirm.call(self);
                }
            });
        },
    });

    module.ErrorInvoiceTransferPopupWidget = module.ErrorPopupWidget.extend({
        template: 'ErrorInvoiceTransferPopupWidget',
    });

    module.UnsentOrdersPopupWidget = module.PopUpWidget.extend({
        template: 'UnsentOrdersPopupWidget',
        show: function(options){
            var self = this;
            this._super(options);
            this.renderElement();
            this.$('.button.confirm').click(function(){
                self.pos_widget.screen_selector.close_popup();
            });
        },
    });

    module.ScaleScreenWidget = module.ScreenWidget.extend({
        template:'ScaleScreenWidget',

        next_screen: 'products',
        previous_screen: 'products',

        show_leftpane:   false,

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

            this.$('.back').click(function(){
                self.pos_widget.screen_selector.set_current_screen(self.previous_screen);
            });

            this.$('.next,.buy-product').click(function(){
                self.order_product();
                self.pos_widget.screen_selector.set_current_screen(self.next_screen);
            });

            queue.schedule(function(){
                return self.pos.proxy.scale_read().then(function(weight){
                    self.set_weight(weight.weight);
                });
            },{duration:50, repeat: true});

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
            return (product ? product.display_name : undefined) || 'Unnamed Product';
        },
        get_product_price: function(){
            var product = this.get_product();
            return (product ? product.price : 0) || 0;
        },
        set_weight: function(weight){
            this.weight = weight;
            this.$('.weight').text(this.get_product_weight_string());
            this.$('.computed-price').text(this.get_computed_price_string());
        },
        get_product_weight_string: function(){
            var product = this.get_product();
            var defaultstr = (this.weight || 0).toFixed(3) + ' Kg';
            if(!product || !this.pos){
                return defaultstr;
            }
            var unit_id = product.uos_id || product.uom_id;
            if(!unit_id){
                return defaultstr;
            }
            var unit = this.pos.units_by_id[unit_id[0]];
            var weight = round_pr(this.weight || 0, unit.rounding);
            var weightstr = weight.toFixed(Math.ceil(Math.log(1.0/unit.rounding) / Math.log(10) ));
                weightstr += ' Kg';
            return weightstr;
        },
        get_computed_price_string: function(){
            return this.format_currency(this.get_product_price() * this.weight);
        },
        close: function(){
            var self = this;
            this._super();
            $('body').off('keyup',this.hotkey_handler);

            this.pos.proxy_queue.clear();
        },
    });

    module.ProductScreenWidget = module.ScreenWidget.extend({
        template:'ProductScreenWidget',

        show_numpad:     true,
        show_leftpane:   true,

        start: function(){ //FIXME this should work as renderElement... but then the categories aren't properly set. explore why
            var self = this;

            this.product_list_widget = new module.ProductListWidget(this,{
                click_product_action: function(product){
                    if(product.to_weight && self.pos.config.iface_electronic_scale){
                        self.pos_widget.screen_selector.set_current_screen('scale',{product: product});
                    }else{
                        self.pos.get('selectedOrder').addProduct(product);
                    }
                },
                product_list: this.pos.db.get_product_by_category(0)
            });
            this.product_list_widget.replace(this.$('.placeholder-ProductListWidget'));

            this.product_categories_widget = new module.ProductCategoriesWidget(this,{
                product_list_widget: this.product_list_widget,
            });
            this.product_categories_widget.replace(this.$('.placeholder-ProductCategoriesWidget'));
        },

        show: function(){
            this._super();
            var self = this;

            this.product_categories_widget.reset_category();

            this.pos_widget.order_widget.set_editable(true);
        },

        close: function(){
            this._super();

            this.pos_widget.order_widget.set_editable(false);

            if(this.pos.config.iface_vkeyboard && this.pos_widget.onscreen_keyboard){
                this.pos_widget.onscreen_keyboard.hide();
            }
        },
    });

    module.ClientListScreenWidget = module.ScreenWidget.extend({
        template: 'ClientListScreenWidget',

        init: function(parent, options){
            this._super(parent, options);
            this.partner_cache = new module.DomCache();
        },

        show_leftpane: false,

        auto_back: true,

        show: function(){
            var self = this;
            this._super();

            this.renderElement();
            this.details_visible = false;
            this.old_client = this.pos.get('selectedOrder').get('client');
            this.new_client = this.old_client;

            this.$('.back').click(function(){
                self.pos_widget.screen_selector.back();
            });

            this.$('.next').click(function(){
                self.save_changes();
                self.pos_widget.screen_selector.back();
            });

            var partners = this.pos.db.get_partners_sorted(1000);
            this.render_list(partners);
            
            this.pos.load_new_partners().then(function(){ 
                // will only get called if new partners were reloaded.
                self.render_list(self.pos.db.get_partners_sorted(1000));
            });

            if( this.old_client ){
                this.display_client_details('show',this.old_client,0);
            }

            this.$('.client-list-contents').delegate('.client-line','click',function(event){
                self.line_select(event,$(this),parseInt($(this).data('id')));
            });

            var search_timeout = null;
            this.$('.searchbox input').on('keyup',function(event){
                clearTimeout(search_timeout);

                var query = this.value;

                search_timeout = setTimeout(function(){
                    self.perform_search(query,event.which === 13);
                },70);
            });

            this.$('.searchbox .search-clear').click(function(){
                self.clear_search();
            });
        },
        perform_search: function(query, associate_result){
            if(query){
                var customers = this.pos.db.search_partner(query);
                this.display_client_details('hide');
                if ( associate_result && customers.length === 1){
                    this.new_client = customers[0];
                    this.save_changes();
                    this.pos_widget.screen_selector.back();
                }
                this.render_list(customers);
            }else{
                var customers = this.pos.db.get_partners_sorted();
                this.render_list(customers);
            }
        },
        clear_search: function(){
            var customers = this.pos.db.get_partners_sorted(1000);
            this.render_list(customers);
            this.$('.searchbox input')[0].value = '';
            this.$('.searchbox input').focus();
        },
        render_list: function(partners){
            var contents = this.$el[0].querySelector('.client-list-contents');
            contents.innerHTML = "";
            for(var i = 0, len = Math.min(partners.length,1000); i < len; i++){
                var partner    = partners[i];
                var clientline = this.partner_cache.get_node(partner.id);
                if(!clientline){
                    var clientline_html = QWeb.render('ClientLine',{widget: this, partner:partners[i]});
                    var clientline = document.createElement('tbody');
                    clientline.innerHTML = clientline_html;
                    clientline = clientline.childNodes[1];
                    this.partner_cache.cache_node(partner.id,clientline);
                }
                if( partners === this.new_client ){
                    clientline.classList.add('highlight');
                }else{
                    clientline.classList.remove('highlight');
                }
                contents.appendChild(clientline);
            }
        },
        save_changes: function(){
            if( this.has_client_changed() ){
                this.pos.get('selectedOrder').set_client(this.new_client);
            }
        },
        has_client_changed: function(){
            if( this.old_client && this.new_client ){
                return this.old_client.id !== this.new_client.id;
            }else{
                return !!this.old_client !== !!this.new_client;
            }
        },
        toggle_save_button: function(){
            var $button = this.$('.button.next');
            if( this.new_client ){
                if( !this.old_client){
                    $button.text(_t('Set Customer'));
                }else{
                    $button.text(_t('Change Customer'));
                }
            }else{
                $button.text(_t('Deselect Customer'));
            }
            $button.toggleClass('oe_hidden',!this.has_client_changed());
        },
        line_select: function(event,$line,id){
            var partner = this.pos.db.get_partner_by_id(id);
            this.$('.client-list .lowlight').removeClass('lowlight');
            if ( $line.hasClass('highlight') ){
                $line.removeClass('highlight');
                $line.addClass('lowlight');
                this.display_client_details('hide',partner);
                this.new_client = null;
                this.toggle_save_button();
            }else{
                this.$('.client-list .highlight').removeClass('highlight');
                $line.addClass('highlight');
                var y = event.pageY - $line.parent().offset().top
                this.display_client_details('show',partner,y);
                this.new_client = partner;
                this.toggle_save_button();
            }
        },
        partner_icon_url: function(id){
            return '/web/binary/image?model=res.partner&id='+id+'&field=image_small';
        },
        display_client_details: function(visibility,partner,clickpos){
            if(visibility === 'show'){
                var contents = this.$('.client-details-contents');
                var parent   = this.$('.client-list').parent();
                var old_scroll   = parent.scrollTop();
                var old_height   = contents.height();
                contents.empty();
                contents.append($(QWeb.render('ClientDetails',{widget:this,partner:partner})));
                var new_height   = contents.height();

                if(!this.details_visible){
                    if(clickpos < old_scroll + new_height + 20 ){
                        parent.scrollTop( clickpos - 20 );
                    }else{
                        parent.scrollTop(parent.scrollTop() + new_height);
                    }
                }else{
                    parent.scrollTop(parent.scrollTop() - old_height + new_height);
                }

                this.details_visible = true;
            }else if(visibility === 'hide'){
                var contents = this.$('.client-details-contents');
                var parent   = this.$('.client-list').parent();
                var scroll   = parent.scrollTop();
                var height   = contents.height();
                contents.empty();
                if( height > scroll ){
                    contents.css({height:height+'px'});
                    contents.animate({height:0},400,function(){
                        contents.css({height:''});
                    });
                    //parent.scrollTop(0);
                }else{
                    parent.scrollTop( parent.scrollTop() - height);
                }
                this.details_visible = false;
            }
        },
        close: function(){
            this._super();
        },
    });

    module.ReceiptScreenWidget = module.ScreenWidget.extend({
        template: 'ReceiptScreenWidget',
        show_numpad:     false,
        show_leftpane:   false,

        show: function(){
            this._super();
            var self = this;

            this.refresh();
            this.print();

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

            this.lock_screen(true);  
            setTimeout(function(){
                self.lock_screen(false);  
            }, 2000);
        },
        lock_screen: function(locked) {
            this._locked = locked;
            if (locked) {
                this.$('.next').removeClass('highlight');
            } else {
                this.$('.next').addClass('highlight');
            }
        },
        print: function() {
            window.print();
        },
        finish_order: function() {
            if (!this._locked) {
                this.pos.get_order().finalize();
            }
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.next').click(function(){
                self.finish_order();
            });
            this.$('.button.print').click(function(){
                self.print();
            });
        },
        refresh: function() {
            var order = this.pos.get_order();
            this.$('.pos-receipt-container').html(QWeb.render('PosTicket',{
                    widget:this,
                    order: order,
                    orderlines: order.get('orderLines').models,
                    paymentlines: order.get('paymentLines').models,
                }));
        },
    });

    module.PaymentScreenWidget = module.ScreenWidget.extend({
        template:      'PaymentScreenWidget',
        back_screen:   'product',
        next_screen:   'receipt',
        show_leftpane: false,
        show_numpad:   false,
        init: function(parent, options) {
            var self = this;
            this._super(parent, options);

            this.pos.bind('change:selectedOrder',function(){
                    this.renderElement();
                    this.watch_order_changes();
                },this);
            this.watch_order_changes();

            this.inputbuffer = "";
            this.firstinput  = true;
            this.keyboard_handler = function(event){
                var key = '';
                if ( event.keyCode === 13 ) {         // Enter
                    self.validate_order();
                } else if ( event.keyCode === 190 ) { // Dot
                    key = '.';
                } else if ( event.keyCode === 46 ) {  // Delete
                    key = 'CLEAR';
                } else if ( event.keyCode === 8 ) {   // Backspace 
                    key = 'BACKSPACE';
                    event.preventDefault(); // Prevents history back nav
                } else if ( event.keyCode >= 48 && event.keyCode <= 57 ){       // Numbers
                    key = '' + (event.keyCode - 48);
                } else if ( event.keyCode >= 96 && event.keyCode <= 105 ){      // Numpad Numbers
                    key = '' + (event.keyCode - 96);
                } else if ( event.keyCode === 189 || event.keyCode === 109 ) {  // Minus
                    key = '-';
                } else if ( event.keyCode === 107 ) { // Plus
                    key = '+';
                }

                self.payment_input(key);

            };
        },
        // resets the current input buffer
        reset_input: function(){
            var line = this.pos.get_order().selected_paymentline;
            this.firstinput  = true;
            if (line) {
                this.inputbuffer = this.format_currency_no_symbol(line.get_amount());
            } else {
                this.inputbuffer = "";
            }
        },
        // handle both keyboard and numpad input. Accepts
        // a string that represents the key pressed.
        payment_input: function(input) {
            var oldbuf = this.inputbuffer.slice(0);

            if (input === '.') {
                if (this.firstinput) {
                    this.inputbuffer = "0.";
                }else if (!this.inputbuffer.length || this.inputbuffer === '-') {
                    this.inputbuffer += "0.";
                } else if (this.inputbuffer.indexOf('.') < 0){
                    this.inputbuffer = this.inputbuffer + '.';
                }
            } else if (input === 'CLEAR') {
                this.inputbuffer = ""; 
            } else if (input === 'BACKSPACE') { 
                this.inputbuffer = this.inputbuffer.substring(0,this.inputbuffer.length - 1);
            } else if (input === '+') {
                if ( this.inputbuffer[0] === '-' ) {
                    this.inputbuffer = this.inputbuffer.substring(1,this.inputbuffer.length);
                }
            } else if (input === '-') {
                if ( this.inputbuffer[0] === '-' ) {
                    this.inputbuffer = this.inputbuffer.substring(1,this.inputbuffer.length);
                } else {
                    this.inputbuffer = '-' + this.inputbuffer;
                }
            } else if (input[0] === '+' && !isNaN(parseFloat(input))) {
                this.inputbuffer = '' + ((parseFloat(this.inputbuffer) || 0) + parseFloat(input));
            } else if (!isNaN(parseInt(input))) {
                if (this.firstinput) {
                    this.inputbuffer = '' + input;
                } else {
                    this.inputbuffer += input;
                }
            }

            this.firstinput = false;

            if (this.inputbuffer !== oldbuf) {
                var order = this.pos.get_order();
                if (order.selected_paymentline) {
                    order.selected_paymentline.set_amount(parseFloat(this.inputbuffer));
                    this.order_changes();
                    this.render_paymentlines();
                    this.$('.paymentline.selected .edit').text(this.inputbuffer);
                }
            }
        },
        click_numpad: function(button) {
            this.payment_input(button.data('action'));
        },
        render_numpad: function() {
            var self = this;
            var numpad = $(QWeb.render('PaymentScreen-Numpad', { widget:this }));
            numpad.on('click','button',function(){
                self.click_numpad($(this));
            });
            return numpad;
        },
        click_delete_paymentline: function(cid){
            var lines = this.pos.get_order().get('paymentLines').models;
            for ( var i = 0; i < lines.length; i++ ) {
                if (lines[i].cid === cid) {
                    this.pos.get_order().removePaymentline(lines[i]);
                    this.reset_input();
                    this.render_paymentlines();
                    return;
                }
            }
        },
        click_paymentline: function(cid){
            var lines = this.pos.get_order().get('paymentLines').models;
            for ( var i = 0; i < lines.length; i++ ) {
                if (lines[i].cid === cid) {
                    this.pos.get_order().selectPaymentline(lines[i]);
                    this.reset_input();
                    this.render_paymentlines();
                    return;
                }
            }
        },
        render_paymentlines: function() {
            var self  = this;
            var order = this.pos.get_order();
            var lines = order.get('paymentLines').models;

            this.$('.paymentlines-container').empty();
            var lines = $(QWeb.render('PaymentScreen-Paymentlines', { 
                widget: this, 
                order: order,
                paymentlines: lines,
            }));

            lines.on('click','.delete-button',function(){
                self.click_delete_paymentline($(this).data('cid'));
            });

            lines.on('click','.paymentline',function(){
                self.click_paymentline($(this).data('cid'));
            });
                
            lines.appendTo(this.$('.paymentlines-container'));
        },
        click_paymentmethods: function(id) {
            var cashregister = null;
            for ( var i = 0; i < this.pos.cashregisters.length; i++ ) {
                if ( this.pos.cashregisters[i].journal_id[0] === id ){
                    cashregister = this.pos.cashregisters[i];
                    break;
                }
            }
            this.pos.get_order().addPaymentline( cashregister );
            this.reset_input();
            this.render_paymentlines();
        },
        render_paymentmethods: function() {
            var self = this;
            var methods = $(QWeb.render('PaymentScreen-Paymentmethods', { widget:this }));
                methods.on('click','.paymentmethod',function(){
                    self.click_paymentmethods($(this).data('id'));
                });
            return methods;
        },
        click_invoice: function(){
            var order = this.pos.get_order();
            order.set_to_invoice(!order.is_to_invoice());
            if (order.is_to_invoice()) {
                this.$('.js_invoice').addClass('highlight');
            } else {
                this.$('.js_invoice').removeClass('highlight');
            }
        },
        renderElement: function() {
            var self = this;
            this._super();

            var numpad = this.render_numpad();
            numpad.appendTo(this.$('.payment-numpad'));

            var methods = this.render_paymentmethods();
            methods.appendTo(this.$('.paymentmethods-container'));

            this.render_paymentlines();

            this.$('.back').click(function(){
                self.pos_widget.screen_selector.back();
            });

            this.$('.next').click(function(){
                self.validate_order();
            });

            this.$('.js_invoice').click(function(){
                self.click_invoice();
            });

        },
        show: function(){
            this.pos.get_order().clean_empty_paymentlines();
            this.reset_input();
            this.render_paymentlines();
            this.order_changes();
            window.document.body.addEventListener('keydown',this.keyboard_handler);
            this._super();
        },
        hide: function(){
            window.document.body.removeEventListener('keydown',this.keyboard_handler);
            this._super();
        },
        // sets up listeners to watch for order changes
        watch_order_changes: function() {
            var self = this;
            var order = this.pos.get_order();
            if(this.old_order){
                this.old_order.unbind(null,null,this);
            }
            order.bind('all',function(){
                self.order_changes();
            });
            this.old_order = order;
        },
        // called when the order is changed, used to show if
        // the order is paid or not
        order_changes: function(){
            var self = this;
            var order = this.pos.get_order();
            if (order.isPaid()) {
                self.$('.next').addClass('highlight');
            }else{
                self.$('.next').removeClass('highlight');
            }
        },
        // Check if the order is paid, then sends it to the backend,
        // and complete the sale process
        validate_order: function() {
            var self = this;

            var order = this.pos.get_order();

            if (!order.isPaid() || this.invoicing) {
                return;
            }

            if (order.isPaidWithCash() && this.pos.config.iface_cashdrawer) { 
                    this.pos.proxy.open_cashbox();
            }

            if (order.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.fail(function(error){
                    self.invoicing = false;
                    if (error === 'error-no-client') {
                        self.pos_widget.screen_selector.show_popup('confirm',{
                            message: _t('Please select the Customer'),
                            comment: _t('You need to select the customer before you can invoice an order.'),
                            confirm: function(){
                                self.pos_widget.screen_selector.set_current_screen('clientlist');
                            },
                        });
                    } else {
                        self.pos_widget.screen_selector.show_popup('error-invoice-transfer');
                    }
                });

                invoiced.done(function(){
                    self.invoicing = false;
                    order.finalize();
                });
            } else {
                this.pos.push_order(order) 
                if (this.pos.config.iface_print_via_proxy) {
                    var receipt = currentOrder.export_for_printing();
                    this.pos.proxy.print_receipt(QWeb.render('XmlReceipt',{
                        receipt: receipt, widget: self,
                    }));
                    order.finalize();    //finish order and go back to scan screen
                } else {
                    this.pos_widget.screen_selector.set_current_screen(this.next_screen);
                }
            }
        },
    });

}
