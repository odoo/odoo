openerp.point_of_sale.load_widgets = function load_widgets(instance, module){ //module is instance.point_of_sale
    "use strict";

    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.DomCache = instance.web.Class.extend({
        init: function(options){
            options = options || {};
            this.max_size = options.max_size || 2000;

            this.cache = {};
            this.access_time = {};
            this.size = 0;
        },
        cache_node: function(key,node){
            var cached = this.cache[key];
            this.cache[key] = node;
            this.access_time[key] = new Date().getTime();
            if(!cached){
                this.size++;
                while(this.size >= this.max_size){
                    var oldest_key = null;
                    var oldest_time = new Date().getTime();
                    for(var key in this.cache){
                        var time = this.access_time[key];
                        if(time <= oldest_time){
                            oldest_time = time;
                            oldest_key  = key;
                        }
                    }
                    if(oldest_key){
                        delete this.cache[oldest_key];
                        delete this.access_time[oldest_key];
                    }
                    this.size--;
                }
            }
            return node;
        },
        get_node: function(key){
            var cached = this.cache[key];
            if(cached){
                this.access_time[key] = new Date().getTime();
            }
            return cached;
        },
    });

    module.NumpadWidget = module.PosBaseWidget.extend({
        template:'NumpadWidget',
        init: function(parent, options) {
            this._super(parent);
            this.state = new module.NumpadState();
            window.numpadstate = this.state;
            var self = this;
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

    // The action pad contains the payment button and the customer selection button
    module.ActionpadWidget = module.PosBaseWidget.extend({
        template: 'ActionpadWidget',
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.pay').click(function(){
                self.gui.show_screen('payment');
            });
            this.$('.set-customer').click(function(){
                self.gui.show_screen('clientlist');
            });
        }
    });

    module.OrderWidget = module.PosBaseWidget.extend({
        template:'OrderWidget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.editable = false;
            this.pos.bind('change:selectedOrder', this.change_selected_order, this);
            this.line_click_handler = function(event){
                if(!self.editable){
                    return;
                }
                self.pos.get_order().select_orderline(this.orderline);
                self.chrome.widget.numpad.state.reset();
            };
            this.client_change_handler = function(event){
                self.update_summary();
            }
            if (this.pos.get_order()) {
                this.bind_order_events();
            }
        },
        enable_numpad: function(){
            this.disable_numpad();  //ensure we don't register the callbacks twice
            this.numpad_state = this.chrome.widget.numpad.state;
            if(this.numpad_state){
                this.numpad_state.reset();
                this.numpad_state.bind('set_value',   this.set_value, this);
            }
                    
        },
        disable_numpad: function(){
            if(this.numpad_state){
                this.numpad_state.unbind('set_value',  this.set_value);
                this.numpad_state.reset();
            }
        },
        set_value: function(val) {
        	var order = this.pos.get_order();
        	if (this.editable && order.get_selected_orderline()) {
                var mode = this.numpad_state.get('mode');
                if( mode === 'quantity'){
                    order.get_selected_orderline().set_quantity(val);
                }else if( mode === 'discount'){
                    order.get_selected_orderline().set_discount(val);
                }else if( mode === 'price'){
                    order.get_selected_orderline().set_unit_price(val);
                }
        	}
        },
        change_selected_order: function() {
            if (this.pos.get_order()) {
                this.bind_order_events();
                this.renderElement();
            }
        },
        orderline_add: function(){
            this.numpad_state.reset();
            this.renderElement('and_scroll_to_bottom');
        },
        orderline_remove: function(line){
            this.remove_orderline(line);
            this.numpad_state.reset();
            this.update_summary();
        },
        orderline_change: function(line){
            this.rerender_orderline(line);
            this.update_summary();
        },
        bind_order_events: function() {
            var order = this.pos.get_order();
                order.unbind('change:client', this.client_change_handler);
                order.bind('change:client', this.client_change_handler);

            var lines = order.orderlines;
                lines.unbind('add',     this.orderline_add,    this);
                lines.bind('add',       this.orderline_add,    this);
                lines.unbind('remove',  this.orderline_remove, this);
                lines.bind('remove',    this.orderline_remove, this); 
                lines.unbind('change',  this.orderline_change, this);
                lines.bind('change',    this.orderline_change, this);

        },
        render_orderline: function(orderline){
            var el_str  = openerp.qweb.render('Orderline',{widget:this, line:orderline}); 
            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];
                el_node.orderline = orderline;
                el_node.addEventListener('click',this.line_click_handler);

            orderline.node = el_node;
            return el_node;
        },
        remove_orderline: function(order_line){
            if(this.pos.get_order().get_orderlines().length === 0){
                this.renderElement();
            }else{
                order_line.node.parentNode.removeChild(order_line.node);
            }
        },
        rerender_orderline: function(order_line){
            var node = order_line.node;
            var replacement_line = this.render_orderline(order_line);
            node.parentNode.replaceChild(replacement_line,node);
        },
        // overriding the openerp framework replace method for performance reasons
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },
        renderElement: function(scrollbottom){
            this.chrome.widget.numpad.state.reset();    //FIXME WTF

            var order  = this.pos.get_order();
            if (!order) {
                return;
            }
            var orderlines = order.get_orderlines();

            var el_str  = openerp.qweb.render('OrderWidget',{widget:this, order:order, orderlines:orderlines});

            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];


            var list_container = el_node.querySelector('.orderlines');
            for(var i = 0, len = orderlines.length; i < len; i++){
                var orderline = this.render_orderline(orderlines[i]);
                list_container.appendChild(orderline);
            }

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;
            this.update_summary();

            if(scrollbottom){
                this.el.querySelector('.order-scroller').scrollTop = 100 * orderlines.length;
            }
        },
        update_summary: function(){
            var order = this.pos.get_order();
            var total     = order ? order.get_total_with_tax() : 0;
            var taxes     = order ? total - order.get_total_without_tax() : 0;

            this.el.querySelector('.summary .total > .value').textContent = this.format_currency(total);
            this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes);

        },
    });

    module.OrderSelectorWidget = module.PosBaseWidget.extend({
        template: 'OrderSelectorWidget',
        init: function(parent, options) {
            this._super(parent, options);
            this.pos.get('orders').bind('add remove change',this.renderElement,this);
            this.pos.bind('change:selectedOrder',this.renderElement,this);
        },
        get_order_by_uid: function(uid) {
            var orders = this.pos.get_order_list();
            for (var i = 0; i < orders.length; i++) {
                if (orders[i].uid === uid) {
                    return orders[i];
                }
            }
            return undefined;
        },
        order_click_handler: function(event,$el) {
            var order = this.get_order_by_uid($el.data('uid'));
            if (order) {
                this.pos.set_order(order);
            }
        },
        neworder_click_handler: function(event, $el) {
            this.pos.add_new_order();
        },
        deleteorder_click_handler: function(event, $el) {
            var self  = this;
            var order = this.pos.get_order(); 
            if (!order) {
                return;
            } else if ( !order.is_empty() ){
                this.gui.show_popup('confirm',{
                    'title': _t('Destroy Current Order ?'),
                    'body': _t('You will lose any data associated with the current order'),
                    confirm: function(){
                        self.pos.delete_current_order();
                    },
                });
            } else {
                this.pos.delete_current_order();
            }
        },
        renderElement: function(){
            var self = this;
            this._super();
            this.$('.order-button.select-order').click(function(event){
                self.order_click_handler(event,$(this));
            });
            this.$('.neworder-button').click(function(event){
                self.neworder_click_handler(event,$(this));
            });
            this.$('.deleteorder-button').click(function(event){
                self.deleteorder_click_handler(event,$(this));
            });
        },
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
            this.product_list_widget = options.product_list_widget || null;
            this.category_cache = new module.DomCache();
            this.set_category();
            
            this.switch_category_handler = function(event){
                self.set_category(self.pos.db.get_category_by_id(Number(this.dataset['categoryId'])));
                self.renderElement();
            };
            
            this.clear_search_handler = function(event){
                self.clear_search();
            };

            var search_timeout  = null;
            this.search_handler = function(event){
                clearTimeout(search_timeout);

                var query = this.value;

                search_timeout = setTimeout(function(){
                    self.perform_search(self.category, query, event.which === 13);
                },70);
            };
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
            return window.location.origin + '/web/binary/image?model=pos.category&field=image_medium&id='+category.id;
        },

        render_category: function( category, with_image ){
            var cached = this.category_cache.get_node(category.id);
            if(!cached){
                if(with_image){
                    var image_url = this.get_image_url(category);
                    var category_html = QWeb.render('CategoryButton',{ 
                            widget:  this, 
                            category: category, 
                            image_url: this.get_image_url(category),
                        });
                        category_html = _.str.trim(category_html);
                    var category_node = document.createElement('div');
                        category_node.innerHTML = category_html;
                        category_node = category_node.childNodes[0];
                }else{
                    var category_html = QWeb.render('CategorySimpleButton',{ 
                            widget:  this, 
                            category: category, 
                        });
                        category_html = _.str.trim(category_html);
                    var category_node = document.createElement('div');
                        category_node.innerHTML = category_html;
                        category_node = category_node.childNodes[0];
                }
                this.category_cache.cache_node(category.id,category_node);
                return category_node;
            }
            return cached; 
        },

        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },

        renderElement: function(){
            var self = this;

            var el_str  = openerp.qweb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
                el_node.innerHTML = el_str;
                el_node = el_node.childNodes[1];

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }

            this.el = el_node;

            var hasimages = false;  //if none of the subcategories have images, we don't display buttons with icons
            for(var i = 0; i < this.subcategories.length; i++){
                if(this.subcategories[i].image){
                    hasimages = true;
                    break;
                }
            }

            var list_container = el_node.querySelector('.category-list');
            if (list_container) { 
                if (!hasimages) {
                    list_container.classList.add('simple');
                } else {
                    list_container.classList.remove('simple');
                }
                for(var i = 0, len = this.subcategories.length; i < len; i++){
                    list_container.appendChild(this.render_category(this.subcategories[i],hasimages));
                };
            }

            var buttons = el_node.querySelectorAll('.js-category-switch');
            for(var i = 0; i < buttons.length; i++){
                buttons[i].addEventListener('click',this.switch_category_handler);
            }

            var products = this.pos.db.get_product_by_category(this.category.id);
            this.product_list_widget.set_product_list(products);

            this.el.querySelector('.searchbox input').addEventListener('keyup',this.search_handler);

            this.el.querySelector('.search-clear').addEventListener('click',this.clear_search_handler);

            if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
                this.chrome.widget.keyboard.connect($(this.el.querySelector('.searchbox input')));
            }
        },
        
        // resets the current category to the root category
        reset_category: function(){
            this.set_category();
            this.renderElement();
        },

        // empties the content of the search box
        clear_search: function(){
            var products = this.pos.db.get_product_by_category(this.category.id);
            this.product_list_widget.set_product_list(products);
            var input = this.el.querySelector('.searchbox input');
                input.value = '';
                input.focus();
        },
        perform_search: function(category, query, buy_result){
            if(query){
                var products = this.pos.db.search_product_in_category(category.id,query)
                if(buy_result && products.length === 1){
                        this.pos.get_order().add_product(products[0]);
                        this.clear_search();
                }else{
                    this.product_list_widget.set_product_list(products);
                }
            }else{
                var products = this.pos.db.get_product_by_category(this.category.id);
                this.product_list_widget.set_product_list(products);
            }
        },

    });

    module.ProductListWidget = module.PosBaseWidget.extend({
        template:'ProductListWidget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.model = options.model;
            this.productwidgets = [];
            this.weight = options.weight || 0;
            this.show_scale = options.show_scale || false;
            this.next_screen = options.next_screen || false;

            this.click_product_handler = function(event){
                var product = self.pos.db.get_product_by_id(this.dataset['productId']);
                options.click_product_action(product);
            };

            this.product_list = options.product_list || [];
            this.product_cache = new module.DomCache();
        },
        set_product_list: function(product_list){
            this.product_list = product_list;
            this.renderElement();
        },
        get_product_image_url: function(product){
            return window.location.origin + '/web/binary/image?model=product.product&field=image_medium&id='+product.id;
        },
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },

        render_product: function(product){
            var cached = this.product_cache.get_node(product.id);
            if(!cached){
                var image_url = this.get_product_image_url(product);
                var product_html = QWeb.render('Product',{ 
                        widget:  this, 
                        product: product, 
                        image_url: this.get_product_image_url(product),
                    });
                var product_node = document.createElement('div');
                product_node.innerHTML = product_html;
                product_node = product_node.childNodes[1];
                this.product_cache.cache_node(product.id,product_node);
                return product_node;
            }
            return cached;
        },

        renderElement: function() {
            var self = this;

            // this._super()
            var el_str  = openerp.qweb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
                el_node.innerHTML = el_str;
                el_node = el_node.childNodes[1];

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;

            var list_container = el_node.querySelector('.product-list');
            for(var i = 0, len = this.product_list.length; i < len; i++){
                var product_node = this.render_product(this.product_list[i]);
                product_node.addEventListener('click',this.click_product_handler);
                list_container.appendChild(product_node);
            };
        },
    });

    module.UsernameWidget = module.PosBaseWidget.extend({
        template: 'UsernameWidget',
        init: function(parent, options){
            var options = options || {};
            this._super(parent,options);
        },
        renderElement: function(){
            var self = this;
            this._super();

            this.$el.click(function(){
                self.click_username();
            });
        },
        click_username: function(){
            var self = this;
            this.gui.select_user({
                'security':     true,
                'current_user': this.pos.get_cashier(),
                'title':      _t('Change Cashier'),
            }).then(function(user){
                self.pos.set_cashier(user);
                self.renderElement();
            });
        },
        get_name: function(){
            var user = this.pos.cashier || this.pos.user;
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
            'open_cashbox',
            'print_receipt',
            'scale_read',
        ],
        minimized: false,
        init: function(parent,options){
            this._super(parent,options);
            var self = this;
            
            this.minimized = false;

            // for dragging the debug widget around
            this.dragging  = false;
            this.dragpos = {x:0, y:0};

            function eventpos(event){
                if(event.touches && event.touches[0]){
                    return {x: event.touches[0].screenX, y: event.touches[0].screenY};
                }else{
                    return {x: event.screenX, y: event.screenY};
                }
            }

            this.dragend_handler = function(event){
                self.dragging = false;
            };
            this.dragstart_handler = function(event){
                self.dragging = true;
                self.dragpos = eventpos(event);
            };
            this.dragmove_handler = function(event){
                if(self.dragging){
                    var top = this.offsetTop;
                    var left = this.offsetLeft;
                    var pos  = eventpos(event);
                    var dx   = pos.x - self.dragpos.x; 
                    var dy   = pos.y - self.dragpos.y; 

                    self.dragpos = pos;

                    this.style.right = 'auto';
                    this.style.bottom = 'auto';
                    this.style.left = left + dx + 'px';
                    this.style.top  = top  + dy + 'px';
                }
                event.preventDefault();
                event.stopPropagation();
            };
        },
        start: function(){
            var self = this;

            this.el.addEventListener('mouseleave', this.dragend_handler);
            this.el.addEventListener('mouseup',    this.dragend_handler);
            this.el.addEventListener('touchend',   this.dragend_handler);
            this.el.addEventListener('touchcancel',this.dragend_handler);
            this.el.addEventListener('mousedown',  this.dragstart_handler);
            this.el.addEventListener('touchstart', this.dragstart_handler);
            this.el.addEventListener('mousemove',  this.dragmove_handler);
            this.el.addEventListener('touchmove',  this.dragmove_handler);

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
                self.pos.barcode_reader.scan(ean);
            });
            this.$('.button.reference').click(function(){
                self.pos.barcode_reader.scan(self.$('input.ean').val());
            });
            this.$('.button.show_orders').click(function(){
                self.gui.show_popup('unsent-orders');
            });
            this.$('.button.delete_orders').click(function(){
                self.gui.show_popup('confirm',{
                    'title': _t('Delete Unsent Orders ?'),
                    'body':  _t('This operation will permanently destroy all unsent orders from the local storage. You will lose all the data. This operation cannot be undone.'),
                    confirm: function(){
                        self.pos.db.remove_all_orders();
                        self.pos.set({synch: { state:'connected', pending: 0 }});
                    },
                });
            });
            this.$('.button.show_unpaid_orders').click(function(){
                self.gui.show_popup('unpaid-orders');
            });
            this.$('.button.delete_unpaid_orders').click(function(){
                self.gui.show_popup('confirm',{
                    'title': _t('Delete Unpaid Orders ?'),
                    'body':  _t('This operation will permanently destroy all unpaid orders from all sessions that have been put in the local storage. You will lose all the data and exit the point of sale. This operation cannot be undone.'),
                    confirm: function(){
                        self.pos.db.remove_all_unpaid_orders();
                        window.location = '/';
                    },
                });
            });
            _.each(this.eans, function(ean, name){
                self.$('.button.'+name).click(function(){
                    self.$('input.ean').val(ean);
                    self.pos.barcode_reader.scan(ean);
                });
            });
            _.each(this.events, function(name){
                self.pos.proxy.add_notification(name,function(){
                    self.$('.event.'+name).stop().clearQueue().css({'background-color':'#6CD11D'}); 
                    self.$('.event.'+name).animate({'background-color':'#1E1E1E'},2000);
                });
            });
        },
    });

// ---------- Main Point of Sale Widget ----------

    module.StatusWidget = module.PosBaseWidget.extend({
        status: ['connected','connecting','disconnected','warning'],
        set_status: function(status,msg){
            var self = this;
            for(var i = 0; i < this.status.length; i++){
                this.$('.js_'+this.status[i]).addClass('oe_hidden');
            }
            this.$('.js_'+status).removeClass('oe_hidden');
            
            if(msg){
                this.$('.js_msg').removeClass('oe_hidden').html(msg);
            }else{
                this.$('.js_msg').addClass('oe_hidden').html('');
            }
        },
    });

    // this is used to notify the user that data is being synchronized on the network
    module.SynchNotificationWidget = module.StatusWidget.extend({
        template: 'SynchNotificationWidget',
        start: function(){
            var self = this;
            this.pos.bind('change:synch', function(pos,synch){
                self.set_status(synch.state, synch.pending);
            });
            this.$el.click(function(){
                self.pos.push_order();
            });
        },
    });

    // this is used to notify the user if the pos is connected to the proxy
    module.ProxyStatusWidget = module.StatusWidget.extend({
        template: 'ProxyStatusWidget',
        set_smart_status: function(status){
            if(status.status === 'connected'){
                var warning = false;
                var msg = ''
                if(this.pos.config.iface_scan_via_proxy){
                    var scanner = status.drivers.scanner ? status.drivers.scanner.status : false;
                    if( scanner != 'connected' && scanner != 'connecting'){
                        warning = true;
                        msg += _t('Scanner');
                    }
                }
                if( this.pos.config.iface_print_via_proxy || 
                    this.pos.config.iface_cashdrawer ){
                    var printer = status.drivers.escpos ? status.drivers.escpos.status : false;
                    if( printer != 'connected' && printer != 'connecting'){
                        warning = true;
                        msg = msg ? msg + ' & ' : msg;
                        msg += _t('Printer');
                    }
                }
                if( this.pos.config.iface_electronic_scale ){
                    var scale = status.drivers.scale ? status.drivers.scale.status : false;
                    if( scale != 'connected' && scale != 'connecting' ){
                        warning = true;
                        msg = msg ? msg + ' & ' : msg;
                        msg += _t('Scale');
                    }
                }
                msg = msg ? msg + ' ' + _t('Offline') : msg;
                this.set_status(warning ? 'warning' : 'connected', msg);
            }else{
                this.set_status(status.status,'');
            }
        },
        start: function(){
            var self = this;
            
            this.set_smart_status(this.pos.proxy.get('status'));

            this.pos.proxy.on('change:status',this,function(eh,status){ //FIXME remove duplicate changes 
                self.set_smart_status(status.newValue);
            });

            this.$el.click(function(){
                self.pos.connect_to_proxy();
            });
        },
    });


    // The Chrome is the main widget that contains all other widgets in the PointOfSale.
    // It is mainly composed of :
    // - a header, containing the list of orders
    // - a leftpane, containing the list of bought products (orderlines) 
    // - a rightpane, containing the screens (see pos_screens.js)
    // - popups
    // - an onscreen keyboard
    // a gui which controls the switching between screens and the showing/closing of popups

    module.Chrome = module.PosBaseWidget.extend({
        template: 'Chrome',
        init: function() { 
            var self = this;
            this._super(arguments[0],{});

            this.started  = new $.Deferred(); // resolves when DOM is onlyne
            this.ready    = new $.Deferred(); // resolves when the whole GUI has been loaded

            this.pos = new module.PosModel(this.session,{chrome:this});
            this.gui = new module.Gui({pos: this.pos, chrome: this});
            this.chrome = this; // So that chrome's childs have chrome set automatically
            this.pos.gui = this.gui;

            this.widget = {};   // contains references to subwidgets instances

            this.numpad_visible = true;
            this.leftpane_visible = true;
            this.leftpane_width   = '440px';
            this.cashier_controls_visible = true;

            this.pos.ready.done(function(){
                self.build_chrome();
                self.pos.on_chrome_started();
                self.started.resolve();
                self.build_widgets();
                self.pos.on_chrome_ready();
                self.ready.resolve();
                self.disable_rubberbanding();
                self.loading_hide();
            }).fail(function(err){   // error when loading models data from the backend
                self.loading_error(err);
            });
        },

        build_chrome: function() { 
            // remove default webclient handlers that induce click delay
            $(document).off();
            $(window).off();
            $('html').off();
            $('body').off();
            $(self.$el).parent().off();
            $('document').off();
            $('.oe_web_client').off();
            $('.openerp_webclient_container').off();

            FastClick.attach(document.body);

            instance.webclient.set_content_full_screen(true);

            this.renderElement();

            if(this.pos.config.iface_big_scrollbars){
                this.$el.addClass('big-scrollbars');
            }
        },

        disable_rubberbanding: function(){
            // prevent the pos body from being scrollable. 
            document.body.addEventListener('touchmove',function(event){
                var node = event.target;
                while(node){
                    if(node.classList && node.classList.contains('touch-scrollable')){
                        return;
                    }
                    node = node.parentNode;
                }
                event.preventDefault();
            });
        },

        loading_error: function(err){
            var self = this;

            var title = err.message;
            var body  = err.stack;

            if(err.message === 'XmlHttpRequestError '){
                title = 'Network Failure (XmlHttpRequestError)';
                body  = 'The Point of Sale could not be loaded due to a network problem.\n Please check your internet connection.';
            }else if(err.message === 'OpenERP Server Error'){
                title = err.data.message;
                body  = err.data.debug;
            }

            if( typeof body !== 'string' ){
                body = 'Traceback not available.';
            }

            var popup = $(QWeb.render('ErrorTracebackPopupWidget',{
                widget: { title: title , body: body },
            }));

            popup.find('.button').click(function(){
                self.close();
            });

            popup.css({ zindex: 9001 });

            popup.appendTo(this.$el);
        },
        loading_progress: function(fac){
            this.$('.loader .loader-feedback').removeClass('oe_hidden');
            this.$('.loader .progress').removeClass('oe_hidden').css({'width': ''+Math.floor(fac*100)+'%'});
        },
        loading_message: function(msg,progress){
            this.$('.loader .loader-feedback').removeClass('oe_hidden');
            this.$('.loader .message').text(msg);
            if (typeof progress !== 'undefined') {
                this.loading_progress(progress);
            } else {
                this.$('.loader .progress').addClass('oe_hidden');
            }
        },
        loading_skip: function(callback){
            if(callback){
                this.$('.loader .loader-feedback').removeClass('oe_hidden');
                this.$('.loader .button.skip').removeClass('oe_hidden');
                this.$('.loader .button.skip').off('click');
                this.$('.loader .button.skip').click(callback);
            }else{
                this.$('.loader .button.skip').addClass('oe_hidden');
            }
        },
        loading_hide: function(){
            this.$('.loader').animate({opacity:0},1500,'swing',function(){self.$('.loader').addClass('oe_hidden');});
        },
        loading_show: function(){
            this.$('.loader').removeClass('oe_hidden').animate({opacity:1},150,'swing');
        },

        screens: {
            'products':     module.ProductScreenWidget,
            'receipt':      module.ReceiptScreenWidget,
            'payment':      module.PaymentScreenWidget,
            'clientlist':   module.ClientListScreenWidget,
            'scale':        module.ScaleScreenWidget,
        },

        popups: {
            'error':            module.ErrorPopupWidget,
            'error-barcode':    module.ErrorBarcodePopupWidget,
            'error-traceback':  module.ErrorTracebackPopupWidget,
            'textinput':        module.TextInputPopupWidget,
            'textarea':         module.TextAreaPopupWidget,
            'number':           module.NumberPopupWidget,
            'password':         module.PasswordPopupWidget,
            'confirm':          module.ConfirmPopupWidget,
            'selection':        module.SelectionPopupWidget,
            'unsent-orders':    module.UnsentOrdersPopupWidget,
            'unpaid-orders':    module.UnpaidOrdersPopupWidget,
        },

        widgets: [
            {
                'name':   'order_selector',
                'widget': module.OrderSelectorWidget,
                'replace':  '.placeholder-OrderSelectorWidget',
            },{
                'name':   'proxy_status',
                'widget': module.ProxyStatusWidget,
                'append':  '.pos-rightheader',
                'condition': function(self){ return self.pos.config.use_proxy },
            },{
                'name':   'notification',
                'widget': module.SynchNotificationWidget,
                'append':  '.pos-rightheader',
            },{
                'name':   'close_button',
                'widget': module.HeaderButtonWidget,
                'append':  '.pos-rightheader',
                'args': {
                    label: _t('Close'),
                    action: function(){ 
                        var self = this;
                        if (!this.confirmed) {
                            this.$el.addClass('confirm');
                            this.$el.text(_t('Confirm'));
                            this.confirmed = setTimeout(function(){
                                self.$el.removeClass('confirm');
                                self.$el.text(_t('Close'));
                                self.confirmed = false;
                            },2000);
                        } else {
                            clearTimeout(this.confirmed);
                            this.chrome.close();
                        }
                    },
                }
            },{
                'name':   'username',
                'widget': module.UsernameWidget,
                'replace':  '.placeholder-UsernameWidget',
            },{
                'name':  'actionpad',
                'widget': module.ActionpadWidget,
                'replace': '.placeholder-ActionpadWidget',
            },{
                'name':  'numpad',
                'widget': module.NumpadWidget,
                'replace': '.placeholder-NumpadWidget',
            },{
                'name':  'order',
                'widget': module.OrderWidget,
                'replace': '.placeholder-OrderWidget',
            },{
                'name':  'keyboard',
                'widget': module.OnscreenKeyboardWidget,
                'replace': '.placeholder-OnscreenKeyboardWidget',
            },{
                'name':  'debug',
                'widget': module.DebugWidget,
                'append': '.pos-content',
                'condition': function(self){ return self.pos.debug },
            },
        ],

        // This method instantiates all the screens, widgets, etc. 
        build_widgets: function() {
            var self = this;

            for (var name in this.screens) {
                var screen = new this.screens[name](this,{});
                    screen.appendTo(this.$('.screens'));
                this.gui.add_screen(name, screen);
            }

            for (var name in this.popups) {
                var popup = new this.popups[name](this,{});
                    popup.appendTo(this.$el);   // FIXME .popups
                this.gui.add_popup(name, popup);
            }

            for (var i = 0; i < this.widgets.length; i++) {
                var def = this.widgets[i];
                if ( !def.condition || def.condition(this) ) {
                    var args = typeof def.args === 'function' ? def.args(this) : def.args;
                    var w = new def.widget(this, args || {});
                    if (def.replace) {
                        w.replace(this.$(def.replace));
                    } else if (def.append) {
                        w.appendTo(this.$(def.append));
                    } else if (def.prepend) {
                        w.prependTo(this.$(def.prepend));
                    } else {
                        w.appendTo(this.$el);
                    }
                    this.widget[def.name] = w;
                }
            }

            this.gui.set_startup_screen('products');
            this.gui.set_default_screen('products');

        },

        // shows or hide the numpad and related controls like the paypad.
        set_numpad_visible: function(visible){
            if(visible !== this.numpad_visible){
                this.numpad_visible = visible;
                if(visible){
                    this.widget.numpad.show();
                    this.widget.actionpad.show();
                }else{
                    this.widget.numpad.hide();
                    this.widget.actionpad.hide();
                }
            }
        },
        //shows or hide the leftpane (contains the list of orderlines, the numpad, the paypad, etc.)
        set_leftpane_visible: function(visible){
            if(visible !== this.leftpane_visible){
                this.leftpane_visible = visible;
                if(visible){
                    this.$('.pos-leftpane').removeClass('oe_hidden');
                    this.$('.rightpane').css({'left':this.leftpane_width});
                }else{
                    this.$('.pos-leftpane').addClass('oe_hidden');
                    this.$('.rightpane').css({'left':'0px'});
                }
            }
        },
        close: function() {
            var self = this;
            self.loading_show();
            self.loading_message(_t('Closing ...'));

            self.pos.push_order().then(function(){
                return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_client_pos_menu']], ['res_id'])
                .pipe(function(res) {
                    window.location = '/web#action=' + res[0]['res_id'];
                },function(err,event) {
                    event.preventDefault();
                    self.gui.show_popup('error',{
                        'title': _t('Could not close the point of sale.'),
                        'body':  _t('Your internet connection is probably down.'),
                    });
                    self.close_button.renderElement();
                });
            });

        },
        destroy: function() {
            this.pos.destroy();
            instance.webclient.set_content_full_screen(false);
            this._super();
        }
    });
}
