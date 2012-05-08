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
                        return Math.round(amount*100)/100 + ' ' + pos.get('currency').symbol;
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
            this.pos_widget = options.pos_widget;
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
            this.pos_widget.action_bar.set_total_value(Math.round(total*100)/100);
            $('#subtotal').html(totalTaxExcluded.toFixed(2)).hide().fadeIn();
            $('#tax').html(tax.toFixed(2)).hide().fadeIn();
            $('#total').html(total.toFixed(2)).hide().fadeIn();
        },
    });

// ---------- Product Screen ----------


    module.ProductWidget = instance.web.Widget.extend({
        tagName:'li',
        template_fct: qweb_template('ProductWidget'),
        init: function(parent, options) {
            this._super(parent);
            this.model = options.model;
            this.pos = options.pos;
            this.model.attributes.weight = options.weight || undefined;
            this.next_screen = options.next_screen || undefined;
        },
        addToOrder: function(event) {
            /* Preserve the category URL */
            event.preventDefault();
            return (this.pos.get('selectedOrder')).addProduct(this.model);
        },
        set_weight: function(weight){
            this.model.attributes.weight = weight;
            this.renderElement();
        },
        set_next_screen: function(screen){
            this.next_screen = screen;
        },
        renderElement: function() {
            var self = this;
            this.$element.addClass("product");
            this.$element.html(this.template_fct(this.model.toJSON()));
            $("a", this.$element).click(function(e){
                self.addToOrder(e);
                if(self.next_screen){
                    self.pos.screen_selector.set_current_screen(self.next_screen);    //FIXME There ought to be a better way to do this ...
                }
            });
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

    module.ActionBarWidget = instance.web.Widget.extend({
        template:'ActionBarWidget',
        init: function(parent, options){
            this._super(parent,options);
            this.button_list = [];
            this.total_visibility = true;
            this.help_visibility  = true;
            this.logout_visibility  = true;
        },
        destroy_buttons:function(){
            for(var i = 0; i < this.button_list.length; i++){
                this.button_list[i].destroy();
            }
            this.button_list = [];
            return this;
        },
        add_new_button: function(button_options){
            if(arguments.length == 1){
                var button = new module.ActionButtonWidget(this,button_options);
                this.button_list.push(button);
                button.appendTo($('.pos-actionbar-button-list'));
            }else{
                for(var i = 0; i < arguments.length; i++){
                    this.add_new_button(arguments[i]);
                }
            }
            return this;
        },
        set_total_visible: function(visible){
            if(visible !== this.total_visibility){
                this.total_visibility = visible;
                if(visible){
                    this.$element.find('.total').show();
                }else{
                    this.$element.find('.total').hide();
                }
            }
        },
        set_help_visible: function(visible,action){
            if(visible !== this.help_visibility){
                this.help_visibility = visible;
                if(visible){
                    this.$element.find('.help-button').show();
                }else{
                    this.$element.find('.help-button').hide();
                }
            }
            if(visible && action){
                this.$element.find('.help-button').off('click').click(action);
            }
        },
        set_logout_visible: function(visible,action){
            if(visible !== this.logout_visibility){
                this.logout_visibility = visible;
                if(visible){
                    this.$element.find('.logout-button').show();
                }else{
                    this.$element.find('.logout-button').hide();
                }
            }
            if(visible && action){
                this.$element.find('.logout-button').off('click').click(action);
            }
        },
        set_total_value: function(value){
            this.$element.find('.value').html(value);
        },
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
            this.product_list = [];
            this.weight = options.weight;
            this.next_screen = options.next_screen || false;
        },
        set_weight: function(weight){
            for(var i = 0; i < this.product_list.length; i++){
                this.product_list[i].set_weight(weight);
            }
        },
        set_next_screen: function(screen){
            for(var i = 0; i < this.product_list.length; i++){
                this.product_list[i].set_next_screen(screen);
            }
        },
        renderElement: function() {
            var self = this;
            this._super();
            this.product_list = []; 
            this.pos.get('products').chain().map(function(product) {
                var product = new module.ProductWidget(this, {
                        model: product,
                        pos: self.pos,
                        weight: self.weight,
                })
                self.product_list.push(product);
                return product;
            }).invoke('appendTo', this.$element);
            return this;
        },
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

// ---------- OnScreen Keyboard Widget ----------

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

// ---------- Main Point of Sale Widget ----------

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
            this.numpad_visible = true;
            this.leftpane_visible = true;
            this.leftpane_width   = '440px';
            this.cashier_controls_visible = true;
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

            this.scan_product_screen = new module.ScanProductScreenWidget(this,{
                pos: this.pos,
                pos_widget: this,
            });
            this.scan_product_screen.appendTo($('#rightpane'));

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

            this.welcome_screen = new module.WelcomeScreenWidget(this,{
                pos:this.pos,
                pos_widget: this,
            });
            this.welcome_screen.appendTo($('#rightpane'));

            this.client_payment_screen = new module.ClientPaymentScreenWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.client_payment_screen.appendTo($('#rightpane'));

            this.scale_invite_screen = new module.ScaleInviteScreenWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.scale_invite_screen.appendTo($('#rightpane'));

            this.scale_product_screen = new module.ScaleProductScreenWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.scale_product_screen.appendTo($('#rightpane'));

            this.help_popup = new module.HelpPopupWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.help_popup.appendTo($('.point-of-sale'));

            this.receipt_popup = new module.ReceiptPopupWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.receipt_popup.appendTo($('.point-of-sale'));

            this.error_popup = new module.ErrorPopupWidget(this, {
                pos: this.pos,
                pos_widget: this,
            });
            this.error_popup.appendTo($('.point-of-sale'));

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
                pos_widget: this,
            });
            this.orderView.$element = $('#current-order-content');
            this.orderView.start();

            this.action_bar = new module.ActionBarWidget(null);
            this.action_bar.appendTo($(".point-of-sale #content"));

            this.onscreen_keyboard = new module.OnscreenKeyboardWidget(null, {
                'keyboard_model': 'simple'
            });
            this.onscreen_keyboard.appendTo($(".point-of-sale #content"));
            
            this.pos.screen_selector = new module.ScreenSelector({
                pos: this.pos,
                screen_set:{
                    'products': this.search_product_screen,
                    'scan': this.scan_product_screen,
                    'payment' : this.payment_screen,
                    'client_payment' : this.client_payment_screen,
                    'scale_invite' : this.scale_invite_screen,
                    'scale_product' : this.scale_product_screen,
                    'receipt' : this.receipt_screen,
                    'welcome' : this.welcome_screen,
                },
                popup_set:{
                    'help': this.help_popup,
                    'error': this.error_popup,
                    'receipt': this.receipt_popup,
                },
                default_client_screen: 'welcome',
                default_cashier_screen: 'products',
                default_mode: 'client',
            });
            window.screen_selector = this.pos.screen_selector;

            this.pos.barcode_reader.connect();
            
        },

        //FIXME this method is probably not at the right place ... 
        scan_product: function(parsed_ean){
            var selectedOrder = this.pos.get('selectedOrder');
            var scannedProductModel = this.get_product_by_ean(parsed_ean.ean);
            if (!scannedProductModel){
                return false;
            } else {
                selectedOrder.addProduct(new module.Product(scannedProductModel));
                return true;
            }
        },

        // returns a product that has a packaging with an EAN matching to provided parsed ean . 
        // returns undefined if no such product is found.
        get_product_by_ean: function(parsed_ean) {
            var allProducts = this.pos.get('product_list');
            var allPackages = this.pos.get('product.packaging');
            var scannedProductModel = undefined;

            if (parsed_ean.type === 'price') {
                var itemCode = parse_result.id;
                var scannedPackaging = _.detect(allPackages, function(pack) { return pack.ean !== undefined && pack.ean.substring(0,7) === itemCode;});
                if (scannedPackaging !== undefined) {
                    scannedProductModel = _.detect(allProducts, function(pc) { return pc.id === scannedPackaging.product_id[0];});
                    scannedProductModel.list_price = parsed_ean.value;
                }
            } else if (parsed_ean.type === 'weight') {
                var weight = parsed_ean.value;
                var itemCode = parsed_ean.id;
                var scannedPackaging = _.detect(allPackages, function(pack) { return pack.ean !== undefined && pack.ean.substring(0,7) === itemCode;});
                if (scannedPackaging !== undefined) {
                    scannedProductModel = _.detect(allProducts, function(pc) { return pc.id === scannedPackaging.product_id[0];});
                    scannedProductModel.list_price *= weight;
                    scannedProductModel.name += ' - ' + weight + ' Kg.';
                }
            } else if(parsed_ean.type === 'unit'){
                scannedProductModel = _.detect(allProducts, function(pc) { return pc.ean13 === parsed_ean.ean;});   //TODO DOES NOT SCALE
            }
            return scannedProductModel;
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
        set_numpad_visible: function(visible){
            if(visible != this.numpad_visible){
                this.numpad_visible = visible;
                if(visible){
                    $('#numpad').show();
                    $('#paypad').show();
                    $('#current-order').css({'bottom':'271px'});
                }else{
                    $('#numpad').hide();
                    $('#paypad').hide();
                    $('#current-order').css({'bottom':'0px'});
                }
            }
        },
        set_leftpane_visible: function(visible){
            if(visible != this.leftpane_visible){
                this.leftpane_visible = visible;
                if(visible){
                    $('#leftpane').show().animate({'width':this.leftpane_width},500,'swing');
                    $('#rightpane').animate({'left':this.leftpane_width},500,'swing');
                }else{
                    var leftpane = $('#leftpane');
                    $('#leftpane').animate({'width':'0px'},500,'swing', function(){ leftpane.hide(); });
                    $('#rightpane').animate({'left':'0px'},500,'swing');
                }
            }
        },
        set_cashier_controls_visible: function(visible){
            if(visible != this.cashier_controls_visible){
                this.cashier_controls_visible = visible;
                if(visible){
                    $('#loggedas').show();
                    $('#rightheader').show();
                }else{
                    $('#loggedas').hide();
                    $('#rightheader').hide();
                }
            }
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
