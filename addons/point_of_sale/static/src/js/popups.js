
// This file contains the Popups.
// Popups must be loaded and named in chrome.js. 
// They are instanciated / destroyed with the .gui.show_popup()
// and .gui.close_popup() methods.

openerp.point_of_sale.load_popups = function load_popups(instance, module) {
    "use strict";

    module.PopupWidget = module.PosBaseWidget.extend({
        init: function(parent, args) {
            this._super(parent, args);
            this.options = {};
        },
        events: {
            'click .button.cancel':  'click_cancel',
            'click .button.confirm': 'click_confirm',
            'click .selection-item': 'click_item',
            'click .input-button':   'click_numpad',
            'click .mode-button':    'click_numpad',
        },

        // show the popup !  
        show: function(options){
            if(this.$el){
                this.$el.removeClass('oe_hidden');
            }
            
            if (typeof options === 'string') {
                this.options = {title: options};
            } else {
                this.options = options || {};
            }

            this.renderElement();

            // popups block the barcode reader ... 
            if (this.pos.barcode_reader) {
                this.pos.barcode_reader.save_callbacks();
                this.pos.barcode_reader.reset_action_callbacks();
            }
        },

        // called before hide, when a popup is closed.
        // extend this if you want a custom action when the 
        // popup is closed.
        close: function(){
            if (this.pos.barcode_reader) {
                this.pos.barcode_reader.restore_callbacks();
            }
        },

        // hides the popup. keep in mind that this is called in 
        // the initialization pass of the pos instantiation, 
        // so you don't want to do anything fancy in here
        hide: function(){
            if (this.$el) {
                this.$el.addClass('oe_hidden');
            }
        },

        // what happens when we click cancel
        // ( it should close the popup and do nothing )
        click_cancel: function(){
            this.gui.close_popup();
            if (this.options.cancel) {
                this.options.cancel.call(this);
            }
        },

        // what happens when we confirm the action
        click_confirm: function(){
            this.gui.close_popup();
            if (this.options.confirm) {
                this.options.confirm.call(this);
            }
        },

        // Since Widget does not support extending the events declaration
        // we declared them all in the top class.
        click_item: function(){},
        click_numad: function(){},
    });


    module.ErrorPopupWidget = module.PopupWidget.extend({
        template:'ErrorPopupWidget',
        show: function(options){
            this._super(options);
            this.gui.play_sound('error');
        },
    });
    module.Gui.define_popup({name:'error', widget:module.ErrorPopupWidget});


    module.ErrorTracebackPopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorTracebackPopupWidget',
    });
    module.Gui.define_popup({name:'error-traceback', widget:module.ErrorTracebackPopupWidget});


    module.ErrorBarcodePopupWidget = module.ErrorPopupWidget.extend({
        template:'ErrorBarcodePopupWidget',
        show: function(barcode){
            this._super({barcode: barcode});
        },
    });
    module.Gui.define_popup({name:'error-barcode', widget:module.ErrorBarcodePopupWidget});


    module.ConfirmPopupWidget = module.PopupWidget.extend({
        template: 'ConfirmPopupWidget',
    });
    module.Gui.define_popup({name:'confirm', widget:module.ConfirmPopupWidget});

    /**
     * A popup that allows the user to select one item from a list. 
     *
     * show_popup('selection',{
     *      title: "Popup Title",
     *      list: [
     *          { label: 'foobar',  item: 45 },
     *          { label: 'bar foo', item: 'stuff' },
     *      ],
     *      confirm: function(item) {
     *          // get the item selected by the user.
     *      },
     *      cancel: function(){
     *          // user chose nothing
     *      }
     *  });
     */

    module.SelectionPopupWidget = module.PopupWidget.extend({
        template: 'SelectionPopupWidget',
        show: function(options){
            options = options || {};
            var self = this;
            this._super(options);

            this.list    = options.list    || [];
            this.renderElement();
        },
        click_item : function(event) {
            this.gui.close_popup();
            if (this.options.confirm) {
                var item = this.list[parseInt($(event.target).data('item-index'))];
                item = item ? item.item : item;
                this.options.confirm.call(self,item);
            }
        }
    });
    module.Gui.define_popup({name:'selection', widget:module.SelectionPopupWidget});


    module.TextInputPopupWidget = module.PopupWidget.extend({
        template: 'TextInputPopupWidget',
        show: function(options){
            options = options || {};
            var self = this;
            this._super(options);

            this.renderElement();
            this.$('input,textarea').focus();
        },
        click_confirm: function(){
            var value = this.$('input,textarea').val();
            this.gui.close_popup();
            if( this.options.confirm ){
                this.options.confirm.call(this,value);
            }
        },
    });
    module.Gui.define_popup({name:'textinput', widget:module.TextInputPopupWidget});


    module.TextAreaPopupWidget = module.TextInputPopupWidget.extend({
        template: 'TextAreaPopupWidget',
    });
    module.Gui.define_popup({name:'textarea', widget:module.TextAreaPopupWidget});


    module.NumberPopupWidget = module.PopupWidget.extend({
        template: 'NumberPopupWidget',
        show: function(options){
            options = options || {};
            var self = this;
            this._super(options);

            this.inputbuffer = '' + (options.value   || '');
            this.decimal_separator = instance.web._t.database.parameters.decimal_point;
            this.renderElement();
            this.firstinput = true;
        },
        click_numpad: function(event){
            var newbuf = this.gui.numpad_input(
                this.inputbuffer, 
                $(event.target).data('action'), 
                {'firstinput': this.firstinput});

            this.firstinput = (newbuf.length === 0);
            
            if (newbuf !== this.inputbuffer) {
                this.inputbuffer = newbuf;
                this.$('.value').text(this.inputbuffer);
            }
        },
        click_confirm: function(event){
            this.gui.close_popup();
            if( this.options.confirm ){
                this.options.confirm.call(this,this.inputbuffer);
            }
        },
    });
    module.Gui.define_popup({name:'number', widget:module.NumberPopupWidget});

    module.PasswordPopupWidget = module.NumberPopupWidget.extend({
        renderElement: function(){
            this._super();
            this.$('.popup').addClass('popup-password');
        },
    });
    module.Gui.define_popup({name:'password', widget:module.PasswordPopupWidget});

    module.UnsentOrdersPopupWidget = module.ConfirmPopupWidget.extend({
        template: 'UnsentOrdersPopupWidget',
    });
    module.Gui.define_popup({name:'unsent-orders', widget:module.UnsentOrdersPopupWidget});

    module.UnpaidOrdersPopupWidget = module.ConfirmPopupWidget.extend({
        template: 'UnpaidOrdersPopupWidget',
    });
    module.Gui.define_popup({name:'unpaid-orders', widget:module.UnpaidOrdersPopupWidget});
};

