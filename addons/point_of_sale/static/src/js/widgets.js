function openerp_pos_widgets(instance, module){ //module is instance.point_of_sale
    var QWeb = instance.web.qweb,
	_t = instance.web._t;

    // The ImageCache is used to hide the latency of the application cache on-disk access in chrome 
    // that causes annoying flickering on product pictures. Why the hell a simple access to
    // the application cache involves such latency is beyond me, hopefully one day this can be
    // removed.
    module.ImageCache   = instance.web.Class.extend({
        init: function(options){
            options = options || {};
            this.max_size = options.max_size || 500;

            this.cache = {};
            this.access_time = {};
            this.size = 0;
        },
        get_image_uncached: function(url){
            var img =  new Image();
            img.src = url;
            return img;
        },
        // returns a DOM Image object from an url, and cache the last 500 (by default) results
        get_image: function(url){
            var cached = this.cache[url];
            if(cached){
                this.access_time[url] = (new Date()).getTime();
                return cached;
            }else{
                var img = new Image();
                img.src = url;
                while(this.size >= this.max_size){
                    var oldestUrl = null;
                    var oldestTime = (new Date()).getTime();
                    for(var url in this.cache){
                        var time = this.access_time[url];
                        if(time <= oldestTime){
                            oldestTime = time;
                            oldestUrl  = url;
                        }
                    }
                    if(oldestUrl){
                        delete this.cache[oldestUrl];
                        delete this.access_time[oldestUrl];
                    }
                    this.size--;
                }
                this.cache[url] = img;
                this.access_time[url] = (new Date()).getTime();
                this.size++;
                return img;
            }
        },
    });

    module.NumpadWidget = module.PosBaseWidget.extend({
        template:'NumpadWidget',
        init: function(parent, options) {
            this._super(parent);
            this.state = new module.NumpadState();
        },
        start: function() {
            this.state.bind('change:mode', this.changedMode, this);
            this.changedMode();
            this.$el.find('.numpad-backspace').click(_.bind(this.clickDeleteLastChar, this));
            this.$el.find('.numpad-minus').click(_.bind(this.clickSwitchSign, this));
            this.$el.find('.number-char').click(_.bind(this.clickAppendNewChar, this));
            this.$el.find('.mode-button').click(_.bind(this.clickChangeMode, this));
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
            $(_.str.sprintf('.mode-button[data-mode="%s"]', mode), this.$el).addClass('selected-mode');
        },
    });

    // The paypad allows to select the payment method (cashRegisters) 
    // used to pay the order.
    module.PaypadWidget = module.PosBaseWidget.extend({
        template: 'PaypadWidget',
        renderElement: function() {
            var self = this;
            this._super();

            this.pos.get('cashRegisters').each(function(cashRegister) {
                var button = new module.PaypadButtonWidget(self,{
                    pos: self.pos,
                    pos_widget : self.pos_widget,
                    cashRegister: cashRegister,
                });
                button.appendTo(self.$el);
            });
        }
    });

    module.PaypadButtonWidget = module.PosBaseWidget.extend({
        template: 'PaypadButtonWidget',
        init: function(parent, options){
            this._super(parent, options);
            this.cashRegister = options.cashRegister;
        },
        renderElement: function() {
            var self = this;
            this._super();

            this.$el.click(function(){
                if (self.pos.get('selectedOrder').get('screen') === 'receipt'){  //TODO Why ?
                    console.warn('TODO should not get there...?');
                    return;
                }
                self.pos.get('selectedOrder').addPaymentLine(self.cashRegister);
                self.pos_widget.screen_selector.set_current_screen('payment');
            });
        },
    });

    module.OrderlineWidget = module.PosBaseWidget.extend({
        template: 'OrderlineWidget',
        init: function(parent, options) {
            this._super(parent,options);

            this.model = options.model;
            this.order = options.order;

            this.model.bind('change', this.refresh, this);
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$el.click(function(){
                self.order.selectLine(self.model);
                self.trigger('order_line_selected');
            });
            if(this.model.is_selected()){
                this.$el.addClass('selected');
            }
        },
        refresh: function(){
            this.renderElement();
            this.trigger('order_line_refreshed');
        },
        destroy: function(){
            this.model.unbind('change',this.refresh,this);
            this._super();
        },
    });
    
    module.OrderWidget = module.PosBaseWidget.extend({
        template:'OrderWidget',
        init: function(parent, options) {
            this._super(parent,options);
            this.display_mode = options.display_mode || 'numpad';   // 'maximized' | 'actionbar' | 'numpad'
            this.set_numpad_state(options.numpadState);
            this.pos.bind('change:selectedOrder', this.change_selected_order, this);
            this.bind_orderline_events();
            this.orderlinewidgets = [];
        },
        set_numpad_state: function(numpadState) {
        	if (this.numpadState) {
        		this.numpadState.unbind('set_value', this.set_value);
        	}
        	this.numpadState = numpadState;
        	if (this.numpadState) {
        		this.numpadState.bind('set_value', this.set_value, this);
        		this.numpadState.reset();
        	}
        },
        set_value: function(val) {
        	var order = this.pos.get('selectedOrder');
        	if (order.get('orderLines').length !== 0) {
                var mode = this.numpadState.get('mode');
                if( mode === 'quantity'){
                    order.getSelectedLine().set_quantity(val);
                }else if( mode === 'discount'){
                    order.getSelectedLine().set_discount(val);
                }else if( mode === 'price'){
                    order.getSelectedLine().set_unit_price(val);
                }
        	}
        },
        change_selected_order: function() {
            this.currentOrderLines.unbind();
            this.bind_orderline_events();
            this.renderElement();
        },
        bind_orderline_events: function() {
            this.currentOrderLines = (this.pos.get('selectedOrder')).get('orderLines');
            this.currentOrderLines.bind('add', function(){ this.renderElement(true);}, this);
            this.currentOrderLines.bind('remove', this.renderElement, this);
        },
        update_numpad: function() {
            this.selected_line = this.pos.get('selectedOrder').getSelectedLine();
            if (this.numpadState)
                this.numpadState.reset();
        },
        renderElement: function(goto_bottom) {
            var self = this;
            var scroller = this.$('.order-scroller')[0];
            var scrollbottom = true;
            var scrollTop = 0;
            if(scroller){
                var overflow_bottom = scroller.scrollHeight - scroller.clientHeight;
                scrollTop = scroller.scrollTop;
                if( !goto_bottom && scrollTop < 0.9 * overflow_bottom){
                    scrollbottom = false;
                }
            }
            this._super();

            // freeing subwidgets
            
            for(var i = 0, len = this.orderlinewidgets.length; i < len; i++){
                this.orderlinewidgets[i].destroy();
            }
            this.orderlinewidgets = [];

            if(this.display_mode === 'maximized'){
                $('.pos .order-container').css({'bottom':'0px'});
            }else if(this.display_mode === 'actionbar'){
                $('.pos .order-container').css({'bottom':'105px'});
            }else if(this.display_mode !== 'numpad'){
                console.error('ERROR: OrderWidget renderElement(): wrong display_mode:',this.display_mode);
            }

            var $content = this.$('.orderlines');
            this.currentOrderLines.each(_.bind( function(orderLine) {
                var line = new module.OrderlineWidget(this, {
                        model: orderLine,
                        order: this.pos.get('selectedOrder'),
                });
            	line.on('order_line_selected', self, self.update_numpad);
                line.on('order_line_refreshed', self, self.update_summary);
                line.appendTo($content);
                self.orderlinewidgets.push(line);
            }, this));
            this.update_numpad();
            this.update_summary();

            scroller = this.$('.order-scroller')[0];
            if(scroller){
                if(scrollbottom){
                    scroller.scrollTop = scroller.scrollHeight - scroller.clientHeight;
                }else{
                    scroller.scrollTop = scrollTop;
                }
            }
        },
        update_summary: function(){
            var order = this.pos.get('selectedOrder');
            var total     = order ? order.getTotalTaxIncluded() : 0;
            var taxes     = order ? total - order.getTotalTaxExcluded() : 0;
            this.$('.summary .total > .value').html(this.format_currency(total));
            this.$('.summary .total .subentry .value').html(this.format_currency(taxes));
        },
        set_display_mode: function(mode){
            if(this.display_mode !== mode){
                this.display_mode = mode;
                this.renderElement();
            }
        },
    });


    module.PaymentlineWidget = module.PosBaseWidget.extend({
        template: 'PaymentlineWidget',
        init: function(parent, options) {
            this._super(parent,options);
            this.payment_line = options.payment_line;
            this.payment_line.bind('change', this.changedAmount, this);
        },
        changeAmount: function(event) {
            var newAmount = event.currentTarget.value;
            var amount = parseFloat(newAmount);
            if(!isNaN(amount)){
                this.amount = amount;
                this.payment_line.set_amount(amount);
            }
        },
        checkAmount: function(e){
            if (e.which !== 0 && e.charCode !== 0) {
                if(isNaN(String.fromCharCode(e.charCode))){
                    return (String.fromCharCode(e.charCode) === "." && e.currentTarget.value.toString().split(".").length < 2)?true:false;
                }
            }
            return true
        },
        changedAmount: function() {
        	if (this.amount !== this.payment_line.get_amount()){
        		this.renderElement();
            }
        },
        renderElement: function() {
            var self = this;
            this.name =   this.payment_line.get_cashregister().get('journal_id')[1];
            this._super();
            this.$('input').keypress(_.bind(this.checkAmount, this))
			.keyup(function(event){
                self.changeAmount(event);
            });
            this.$('.delete-payment-line').click(function() {
                self.trigger('delete_payment_line', self);
            });
        },
        focus: function(){
            var val = this.$('input')[0].value;
            this.$('input')[0].focus();
            this.$('input')[0].value = val;
            this.$('input')[0].select();
        },
    });

    module.OrderButtonWidget = module.PosBaseWidget.extend({
        template:'OrderButtonWidget',
        init: function(parent, options) {
            this._super(parent,options);
            var self = this;

            this.order = options.order;
            this.order.bind('destroy',this.destroy, this );
            this.order.bind('change', this.renderElement, this );
            this.pos.bind('change:selectedOrder', this.renderElement,this );
        },
        renderElement:function(){
            this._super();
            var self = this;
            this.$el.click(function(){ 
                self.selectOrder();
            });
            if( this.order === this.pos.get('selectedOrder') ){
                this.$el.addClass('selected-order');
            }
        },
        selectOrder: function(event) {
            this.pos.set({
                selectedOrder: this.order
            });
        },
        destroy: function(){
            this.order.unbind('destroy', this.destroy, this);
            this.order.unbind('change',  this.renderElement, this);
            this.pos.unbind('change:selectedOrder', this.renderElement, this);
            this._super();
        },
    });

    module.ActionButtonWidget = instance.web.Widget.extend({
        template:'ActionButtonWidget',
        icon_template:'ActionButtonWidgetWithIcon',
        init: function(parent, options){
            this._super(parent, options);
            this.label = options.label || 'button';
            this.rightalign = options.rightalign || false;
            this.click_action = options.click;
            this.disabled = options.disabled || false;
            if(options.icon){
                this.icon = options.icon;
                this.template = this.icon_template;
            }
        },
        set_disabled: function(disabled){
            if(this.disabled != disabled){
                this.disabled = !!disabled;
                this.renderElement();
            }
        },
        renderElement: function(){
            this._super();
            if(this.click_action && !this.disabled){
                this.$el.click(_.bind(this.click_action, this));
            }
        },
    });

    module.ActionBarWidget = instance.web.Widget.extend({
        template:'ActionBarWidget',
        init: function(parent, options){
            this._super(parent,options);
            this.button_list = [];
            this.buttons = {};
            this.visibility = {};
        },
        set_element_visible: function(element, visible, action){
            if(visible != this.visibility[element]){
                this.visibility[element] = !!visible;
                if(visible){
                    this.$('.'+element).removeClass('oe_hidden');
                }else{
                    this.$('.'+element).addClass('oe_hidden');
                }
            }
            if(visible && action){
                this.action[element] = action;
                this.$('.'+element).off('click').click(action);
            }
        },
        set_button_disabled: function(name, disabled){
            var b = this.buttons[name];
            if(b){
                b.set_disabled(disabled);
            }
        },
        destroy_buttons:function(){
            for(var i = 0; i < this.button_list.length; i++){
                this.button_list[i].destroy();
            }
            this.button_list = [];
            this.buttons = {};
            return this;
        },
        get_button_count: function(){
            return this.button_list.length;
        },
        add_new_button: function(button_options){
            var button = new module.ActionButtonWidget(this,button_options);
            this.button_list.push(button);
            if(button_options.name){
                this.buttons[button_options.name] = button;
            }
            button.appendTo(this.$('.pos-actionbar-button-list'));
            return button;
        },
        show:function(){
            this.$el.removeClass('oe_hidden');
        },
        hide:function(){
            this.$el.addClass('oe_hidden');
        },
    });

    module.CategoryButton = module.PosBaseWidget.extend({
    });
    module.ProductCategoriesWidget = module.PosBaseWidget.extend({
        template: 'ProductCategoriesWidget',
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            this.product_type = options.product_type || 'all';  // 'all' | 'weightable'
            this.onlyWeightable = options.onlyWeightable || false;
            this.category = this.pos.root_category;
            this.breadcrumb = [];
            this.subcategories = [];
            this.set_category();
        },

        // changes the category. if undefined, sets to root category
        set_category : function(category){
            var db = this.pos.db;
            if(!category){
                this.category = db.get_category_by_id(db.root_category_id);
            }else{
                this.category = category;
            }
            this.breadcrumb = [];
            var ancestors_ids = db.get_category_ancestors_ids(this.category.id);
            for(var i = 1; i < ancestors_ids.length; i++){
                this.breadcrumb.push(db.get_category_by_id(ancestors_ids[i]));
            }
            if(this.category.id !== db.root_category_id){
                this.breadcrumb.push(this.category);
            }
            this.subcategories = db.get_category_by_id(db.get_category_childs_ids(this.category.id));
        },

        get_image_url: function(category){
            return instance.session.url('/web/binary/image', {model: 'pos.category', field: 'image_medium', id: category.id});
        },

        renderElement: function(){
            var self = this;
            this._super();

            var hasimages = false;  //if none of the subcategories have images, we don't display buttons with icons
            _.each(this.subcategories, function(category){
                if(category.image){
                    hasimages = true;
                }
            });

            _.each(this.subcategories, function(category){
                if(hasimages){
                    var button = QWeb.render('CategoryButton',{category:category});
                    var button = _.str.trim(button);
                    var button = $(button);
                    button.find('img').replaceWith(self.pos_widget.image_cache.get_image(self.get_image_url(category)));
                }else{
                    var button = QWeb.render('CategorySimpleButton',{category:category});
                    button = _.str.trim(button);    // we remove whitespace between buttons to fix spacing
                    var button = $(button);
                }

                button.appendTo(this.$('.category-list')).click(function(event){
                    var id = category.id;
                    var cat = self.pos.db.get_category_by_id(id);
                    self.set_category(cat);
                    self.renderElement();
                });
            });
            // breadcrumb click actions
            this.$(".oe-pos-categories-list a").click(function(event){
                var id = $(event.target).data("category-id");
                var category = self.pos.db.get_category_by_id(id);
                self.set_category(category);
                self.renderElement();
            });

            this.search_and_categories();

            if(this.pos.iface_vkeyboard && this.pos_widget.onscreen_keyboard){
                this.pos_widget.onscreen_keyboard.connect(this.$('.searchbox input'));
            }
        },
        
        set_product_type: function(type){       // 'all' | 'weightable'
            this.product_type = type;
            this.reset_category();
        },

        // resets the current category to the root category
        reset_category: function(){
            this.set_category();
            this.renderElement();
        },

        // empties the content of the search box
        clear_search: function(){
            var products = this.pos.db.get_product_by_category(this.category.id);
            this.pos.get('products').reset(products);
            this.$('.searchbox input').val('').focus();
            this.$('.search-clear').fadeOut();
        },

        // filters the products, and sets up the search callbacks
        search_and_categories: function(category){
            var self = this;

            // find all products belonging to the current category
            var products = this.pos.db.get_product_by_category(this.category.id);
            self.pos.get('products').reset(products);

            // filter the products according to the search string
            this.$('.searchbox input').keyup(function(event){
                console.log('event',event);
                query = $(this).val().toLowerCase();
                if(query){
                    if(event.which === 13){
                        if( self.pos.get('products').size() === 1 ){
                            self.pos.get('selectedOrder').addProduct(self.pos.get('products').at(0));
                            self.clear_search();
                        }
                    }else{
                        var products = self.pos.db.search_product_in_category(self.category.id, query);
                        self.pos.get('products').reset(products);
                        self.$('.search-clear').fadeIn();
                    }
                }else{
                    var products = self.pos.db.get_product_by_category(self.category.id);
                    self.pos.get('products').reset(products);
                    self.$('.search-clear').fadeOut();
                }
            });

            //reset the search when clicking on reset
            this.$('.search-clear').click(function(){
                self.clear_search();
            });
        },
    });

    module.ProductListWidget = module.ScreenWidget.extend({
        template:'ProductListWidget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.model = options.model;
            this.productwidgets = [];
            this.weight = options.weight || 0;
            this.show_scale = options.show_scale || false;
            this.next_screen = options.next_screen || false;
            this.click_product_action = options.click_product_action;

            this.pos.get('products').bind('reset', function(){
                self.renderElement();
            });
        },
        renderElement: function() {
            var self = this;
            this._super();

            var products = this.pos.get('products').models || [];

            _.each(products,function(product,i){
                var $product = $(QWeb.render('Product',{ widget:self, product: products[i] }));
                $product.find('img').replaceWith(self.pos_widget.image_cache.get_image(products[i].get_image_url()));
                $product.appendTo(self.$('.product-list'));
            });
            this.$el.delegate('a','click',function(){ 
                self.click_product_action(new module.Product(self.pos.db.get_product_by_id(+$(this).data('product-id')))); 
            });

        },
    });

    module.UsernameWidget = module.PosBaseWidget.extend({
        template: 'UsernameWidget',
        init: function(parent, options){
            var options = options || {};
            this._super(parent,options);
            this.mode = options.mode || 'cashier';
        },
        set_user_mode: function(mode){
            this.mode = mode;
            this.refresh();
        },
        refresh: function(){
            this.renderElement();
        },
        get_name: function(){
            var user;
            if(this.mode === 'cashier'){
                user = this.pos.get('cashier') || this.pos.get('user');
            }else{
                user = this.pos.get('selectedOrder').get_client()  || this.pos.get('user');
            }
            if(user){
                return user.name;
            }else{
                return "";
            }
        },
    });

    module.HeaderButtonWidget = module.PosBaseWidget.extend({
        template: 'HeaderButtonWidget',
        init: function(parent, options){
            options = options || {};
            this._super(parent, options);
            this.action = options.action;
            this.label   = options.label;
        },
        renderElement: function(){
            var self = this;
            this._super();
            if(this.action){
                this.$el.click(function(){
                    self.action();
                });
            }
        },
        show: function(){ this.$el.removeClass('oe_hidden'); },
        hide: function(){ this.$el.addClass('oe_hidden'); },
    });

    // The debug widget lets the user control and monitor the hardware and software status
    // without the use of the proxy
    module.DebugWidget = module.PosBaseWidget.extend({
        template: "DebugWidget",
        eans:{
            admin_badge:  '0410100000006',
            client_badge: '0420200000004',
            invalid_ean:  '1232456',
            soda_33cl:    '5449000000996',
            oranges_kg:   '2100002031410',
            lemon_price:  '2301000001560',
            unknown_product: '9900000000004',
        },
        events:[
            'scan_item_success',
            'scan_item_error_unrecognized',
            'payment_request',
            'open_cashbox',
            'print_receipt',
            'print_pdf_invoice',
            'weighting_read_kg',
            'payment_status',
        ],
        minimized: false,
        start: function(){
            var self = this;

            this.$el.draggable();
            this.$('.toggle').click(function(){
                var content = self.$('.content');
                var bg      = self.$el;
                if(!self.minimized){
                    content.animate({'height':'0'},200);
                }else{
                    content.css({'height':'auto'});
                }
                self.minimized = !self.minimized;
            });
            this.$('.button.accept_payment').click(function(){
                self.pos.proxy.debug_accept_payment();
            });
            this.$('.button.reject_payment').click(function(){
                self.pos.proxy.debug_reject_payment();
            });
            this.$('.button.set_weight').click(function(){
                var kg = Number(self.$('input.weight').val());
                if(!isNaN(kg)){
                    self.pos.proxy.debug_set_weight(kg);
                }
            });
            this.$('.button.reset_weight').click(function(){
                self.$('input.weight').val('');
                self.pos.proxy.debug_reset_weight();
            });
            this.$('.button.custom_ean').click(function(){
                var ean = self.pos.barcode_reader.sanitize_ean(self.$('input.ean').val() || '0');
                self.$('input.ean').val(ean);
                self.pos.barcode_reader.scan('ean13',ean);
            });
            this.$('.button.reference').click(function(){
                self.pos.barcode_reader.scan('reference',self.$('input.ean').val());
            });
            _.each(this.eans, function(ean, name){
                self.$('.button.'+name).click(function(){
                    self.$('input.ean').val(ean);
                    self.pos.barcode_reader.scan('ean13',ean);
                });
            });
            _.each(this.events, function(name){
                self.pos.proxy.add_notification(name,function(){
                    self.$('.event.'+name).stop().clearQueue().css({'background-color':'#6CD11D'}); 
                    self.$('.event.'+name).animate({'background-color':'#1E1E1E'},2000);
                });
            });
            self.pos.proxy.add_notification('help_needed',function(){
                self.$('.status.help_needed').addClass('on');
            });
            self.pos.proxy.add_notification('help_canceled',function(){
                self.$('.status.help_needed').removeClass('on');
            });
            self.pos.proxy.add_notification('transaction_start',function(){
                self.$('.status.transaction').addClass('on');
            });
            self.pos.proxy.add_notification('transaction_end',function(){
                self.$('.status.transaction').removeClass('on');
            });
            self.pos.proxy.add_notification('weighting_start',function(){
                self.$('.status.weighting').addClass('on');
            });
            self.pos.proxy.add_notification('weighting_end',function(){
                self.$('.status.weighting').removeClass('on');
            });
        },
    });

// ---------- Main Point of Sale Widget ----------

    // this is used to notify the user that data is being synchronized on the network
    module.SynchNotificationWidget = module.PosBaseWidget.extend({
        template: "SynchNotificationWidget",
        init: function(parent, options){
            options = options || {};
            this._super(parent, options);
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.$el.click(function(){
                self.pos.flush();
            });
        },
        start: function(){
            var self = this;
            this.pos.bind('change:nbr_pending_operations', function(){
                self.renderElement();
            });
        },
        get_nbr_pending: function(){
            return this.pos.get('nbr_pending_operations');
        },
    });


    // The PosWidget is the main widget that contains all other widgets in the PointOfSale.
    // It is mainly composed of :
    // - a header, containing the list of orders
    // - a leftpane, containing the list of bought products (orderlines) 
    // - a rightpane, containing the screens (see pos_screens.js)
    // - an actionbar on the bottom, containing various action buttons
    // - popups
    // - an onscreen keyboard
    // a screen_selector which controls the switching between screens and the showing/closing of popups

    module.PosWidget = module.PosBaseWidget.extend({
        template: 'PosWidget',
        init: function() { 
            this._super(arguments[0],{});

            instance.web.blockUI(); 

            this.pos = new module.PosModel(this.session);
            this.pos.pos_widget = this;
            this.pos_widget = this; //So that pos_widget's childs have pos_widget set automatically

            this.numpad_visible = true;
            this.left_action_bar_visible = true;
            this.leftpane_visible = true;
            this.leftpane_width   = '440px';
            this.cashier_controls_visible = true;
            this.image_cache = new module.ImageCache(); // for faster products image display

            FastClick.attach(document.body);

        },
      
        start: function() {
            var self = this;
            return self.pos.ready.done(function() {
                $('.oe_tooltip').remove();  // remove tooltip from the start session button

                self.build_currency_template();
                self.renderElement();
                
                self.$('.neworder-button').click(function(){
                    self.pos.add_new_order();
                });

                self.$('.deleteorder-button').click(function(){
                    self.pos.delete_current_order();
                });
                
                //when a new order is created, add an order button widget
                self.pos.get('orders').bind('add', function(new_order){
                    var new_order_button = new module.OrderButtonWidget(null, {
                        order: new_order,
                        pos: self.pos
                    });
                    new_order_button.appendTo(this.$('.orders'));
                    new_order_button.selectOrder();
                }, self);

                self.pos.add_new_order();

                self.build_widgets();

                self.screen_selector.set_default_screen();


                self.pos.barcode_reader.connect();

                instance.webclient.set_content_full_screen(true);

                if (!self.pos.get('pos_session')) {
                    self.screen_selector.show_popup('error', 'Sorry, we could not create a user session');
                }else if(!self.pos.get('pos_config')){
                    self.screen_selector.show_popup('error', 'Sorry, we could not find any PoS Configuration for this session');
                }
            
                instance.web.unblockUI();
                self.$('.loader').animate({opacity:0},1500,'swing',function(){self.$('.loader').addClass('oe_hidden');});

                self.pos.flush();

            }).fail(function(){   // error when loading models data from the backend
                instance.web.unblockUI();
                return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_pos_session_opening']], ['res_id'])
                    .pipe( _.bind(function(res){
                        return instance.session.rpc('/web/action/load', {'action_id': res[0]['res_id']})
                            .pipe(_.bind(function(result){
                                var action = result.result;
                                this.do_action(action);
                            }, this));
                    }, self));
            });
        },
        
        // This method instantiates all the screens, widgets, etc. If you want to add new screens change the
        // startup screen, etc, override this method.
        build_widgets: function() {
            var self = this;

            // --------  Screens ---------

            this.product_screen = new module.ProductScreenWidget(this,{});
            this.product_screen.appendTo(this.$('.pos-rightpane'));

            this.receipt_screen = new module.ReceiptScreenWidget(this, {});
            this.receipt_screen.appendTo(this.$('.pos-rightpane'));

            this.payment_screen = new module.PaymentScreenWidget(this, {});
            this.payment_screen.appendTo(this.$('.pos-rightpane'));

            this.welcome_screen = new module.WelcomeScreenWidget(this,{});
            this.welcome_screen.appendTo(this.$('.pos-rightpane'));

            this.client_payment_screen = new module.ClientPaymentScreenWidget(this, {});
            this.client_payment_screen.appendTo(this.$('.pos-rightpane'));

            this.scale_invite_screen = new module.ScaleInviteScreenWidget(this, {});
            this.scale_invite_screen.appendTo(this.$('.pos-rightpane'));

            this.scale_screen = new module.ScaleScreenWidget(this,{});
            this.scale_screen.appendTo(this.$('.pos-rightpane'));

            // --------  Popups ---------

            this.help_popup = new module.HelpPopupWidget(this, {});
            this.help_popup.appendTo(this.$el);

            this.error_popup = new module.ErrorPopupWidget(this, {});
            this.error_popup.appendTo(this.$el);

            this.error_product_popup = new module.ProductErrorPopupWidget(this, {});
            this.error_product_popup.appendTo(this.$el);

            this.error_session_popup = new module.ErrorSessionPopupWidget(this, {});
            this.error_session_popup.appendTo(this.$el);

            this.choose_receipt_popup = new module.ChooseReceiptPopupWidget(this, {});
            this.choose_receipt_popup.appendTo(this.$el);

            this.error_negative_price_popup = new module.ErrorNegativePricePopupWidget(this, {});
            this.error_negative_price_popup.appendTo(this.$el);

            this.error_no_client_popup = new module.ErrorNoClientPopupWidget(this, {});
            this.error_no_client_popup.appendTo(this.$el);

            this.error_invoice_transfer_popup = new module.ErrorInvoiceTransferPopupWidget(this, {});
            this.error_invoice_transfer_popup.appendTo(this.$el);

            // --------  Misc ---------

            this.notification = new module.SynchNotificationWidget(this,{});
            this.notification.appendTo(this.$('.pos-rightheader'));

            this.username   = new module.UsernameWidget(this,{});
            this.username.replace(this.$('.placeholder-UsernameWidget'));

            this.action_bar = new module.ActionBarWidget(this);
            this.action_bar.appendTo(this.$(".pos-rightpane"));

            this.left_action_bar = new module.ActionBarWidget(this);
            this.left_action_bar.replace(this.$('.placeholder-LeftActionBar'));

            this.paypad = new module.PaypadWidget(this, {});
            this.paypad.replace(this.$('.placeholder-PaypadWidget'));

            this.numpad = new module.NumpadWidget(this);
            this.numpad.replace(this.$('.placeholder-NumpadWidget'));

            this.order_widget = new module.OrderWidget(this, {});
            this.order_widget.replace(this.$('.placeholder-OrderWidget'));

            this.onscreen_keyboard = new module.OnscreenKeyboardWidget(this, {
                'keyboard_model': 'simple'
            });
            this.onscreen_keyboard.replace(this.$('.placeholder-OnscreenKeyboardWidget'));

            this.close_button = new module.HeaderButtonWidget(this,{
                label: _t('Close'),
                action: function(){ self.close(); },
            });
            this.close_button.appendTo(this.$('.pos-rightheader'));

            this.client_button = new module.HeaderButtonWidget(this,{
                label: _t('Self-Checkout'),
                action: function(){ self.screen_selector.set_user_mode('client'); },
            });
            this.client_button.appendTo(this.$('.pos-rightheader'));

            
            // --------  Screen Selector ---------

            this.screen_selector = new module.ScreenSelector({
                pos: this.pos,
                screen_set:{
                    'products': this.product_screen,
                    'payment' : this.payment_screen,
                    'client_payment' : this.client_payment_screen,
                    'scale_invite' : this.scale_invite_screen,
                    'scale':    this.scale_screen,
                    'receipt' : this.receipt_screen,
                    'welcome' : this.welcome_screen,
                },
                popup_set:{
                    'help': this.help_popup,
                    'error': this.error_popup,
                    'error-product': this.error_product_popup,
                    'error-session': this.error_session_popup,
                    'error-negative-price': this.error_negative_price_popup,
                    'choose-receipt': this.choose_receipt_popup,
                    'error-no-client': this.error_no_client_popup,
                    'error-invoice-transfer': this.error_invoice_transfer_popup,
                },
                default_client_screen: 'welcome',
                default_cashier_screen: 'products',
                default_mode: this.pos.iface_self_checkout ?  'client' : 'cashier',
            });

            if(this.pos.debug){
                this.debug_widget = new module.DebugWidget(this);
                this.debug_widget.appendTo(this.$('.pos-content'));
            }
        },

        changed_pending_operations: function () {
            var self = this;
            this.synch_notification.on_change_nbr_pending(self.pos.get('nbr_pending_operations').length);
        },
        // shows or hide the numpad and related controls like the paypad.
        set_numpad_visible: function(visible){
            if(visible !== this.numpad_visible){
                this.numpad_visible = visible;
                if(visible){
                    this.set_left_action_bar_visible(false);
                    this.numpad.show();
                    this.paypad.show();
                    this.order_widget.set_display_mode('numpad');
                }else{
                    this.numpad.hide();
                    this.paypad.hide();
                    if(this.order_widget.display_mode === 'numpad'){
                        this.order_widget.set_display_mode('maximized');
                    }
                }
            }
        },
        set_left_action_bar_visible: function(visible){
            if(visible !== this.left_action_bar_visible){
                this.left_action_bar_visible = visible;
                if(visible){
                    this.set_numpad_visible(false);
                    this.left_action_bar.show();
                    this.order_widget.set_display_mode('actionbar');
                }else{
                    this.left_action_bar.hide();
                    if(this.order_widget.display_mode === 'actionbar'){
                        this.order_widget.set_display_mode('maximized');
                    }
                }
            }
        },

        //shows or hide the leftpane (contains the list of orderlines, the numpad, the paypad, etc.)
        set_leftpane_visible: function(visible){
            if(visible !== this.leftpane_visible){
                this.leftpane_visible = visible;
                if(visible){
                    this.$('.pos-leftpane').removeClass('oe_hidden').animate({'width':this.leftpane_width},500,'swing');
                    this.$('.pos-rightpane').animate({'left':this.leftpane_width},500,'swing');
                }else{
                    var leftpane = this.$('.pos-leftpane');
                    leftpane.animate({'width':'0px'},500,'swing', function(){ leftpane.addClass('oe_hidden'); });
                    this.$('.pos-rightpane').animate({'left':'0px'},500,'swing');
                }
            }
        },
        //shows or hide the controls in the PosWidget that are specific to the cashier ( Orders, close button, etc. ) 
        set_cashier_controls_visible: function(visible){
            if(visible !== this.cashier_controls_visible){
                this.cashier_controls_visible = visible;
                if(visible){
                    this.$('.pos-rightheader').removeClass('oe_hidden');
                }else{
                    this.$('.pos-rightheader').addClass('oe_hidden');
                }
            }
        },
        close: function() {
            var self = this;

            function close(){
                return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_client_pos_menu']], ['res_id']).pipe(
                        _.bind(function(res) {
                    return this.rpc('/web/action/load', {'action_id': res[0]['res_id']}).pipe(_.bind(function(result) {
                        var action = result;
                        action.context = _.extend(action.context || {}, {'cancel_action': {type: 'ir.actions.client', tag: 'reload'}});
                        //self.destroy();
                        this.do_action(action);
                    }, this));
                }, self));
            }

            var draft_order = _.find( self.pos.get('orders').models, function(order){
                return order.get('orderLines').length !== 0 && order.get('paymentLines').length === 0;
            });
            if(draft_order){
                if (confirm(_t("Pending orders will be lost.\nAre you sure you want to leave this session?"))) {
                    return close();
                }
            }else{
                return close();
            }
        },
        destroy: function() {
            this.pos.destroy();
            instance.webclient.set_content_full_screen(false);
            this._super();
        }
    });
}
