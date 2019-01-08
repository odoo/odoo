odoo.define('point_of_sale.popups', function (require) {
"use strict";

// This file contains the Popups.
// Popups must be loaded and named in chrome.js.
// They are instanciated / destroyed with the .gui.show_popup()
// and .gui.close_popup() methods.

var PosBaseWidget = require('point_of_sale.BaseWidget');
var gui = require('point_of_sale.gui');
var _t  = require('web.core')._t;


var PopupWidget = PosBaseWidget.extend({
    template: 'PopupWidget',
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
gui.define_popup({name:'alert', widget: PopupWidget});

var ErrorPopupWidget = PopupWidget.extend({
    template:'ErrorPopupWidget',
    show: function(options){
        this._super(options);
        this.gui.play_sound('error');
    },
});
gui.define_popup({name:'error', widget: ErrorPopupWidget});


var ErrorTracebackPopupWidget = ErrorPopupWidget.extend({
    template:'ErrorTracebackPopupWidget',
    show: function(opts) {
        var self = this;
        this._super(opts);

        this.$('.download').off('click').click(function(){
            self.gui.prepare_download_link(self.options.body,
                _t('error') + ' ' + moment().format('YYYY-MM-DD-HH-mm-ss') + '.txt',
                '.download', '.download_error_file');
        });

        this.$('.email').off('click').click(function(){
            self.gui.send_email( self.pos.company.email,
                _t('IMPORTANT: Bug Report From Odoo Point Of Sale'),
                self.options.body);
        });
    }
});
gui.define_popup({name:'error-traceback', widget: ErrorTracebackPopupWidget});


var ErrorBarcodePopupWidget = ErrorPopupWidget.extend({
    template:'ErrorBarcodePopupWidget',
    show: function(barcode){
        this._super({barcode: barcode});
    },
});
gui.define_popup({name:'error-barcode', widget: ErrorBarcodePopupWidget});


var ConfirmPopupWidget = PopupWidget.extend({
    template: 'ConfirmPopupWidget',
});
gui.define_popup({name:'confirm', widget: ConfirmPopupWidget});

/**
 * A popup that allows the user to select one item from a list.
 *
 * Example::
 *
 *    show_popup('selection',{
 *        title: "Popup Title",
 *        list: [
 *            { label: 'foobar',  item: 45 },
 *            { label: 'bar foo', item: 'stuff' },
 *        ],
 *        confirm: function(item) {
 *            // get the item selected by the user.
 *        },
 *        cancel: function(){
 *            // user chose nothing
 *        }
 *    });
 */

var SelectionPopupWidget = PopupWidget.extend({
    template: 'SelectionPopupWidget',
    show: function(options){
        var self = this;
        options = options || {};
        this._super(options);

        this.list = options.list || [];
        this.is_selected = options.is_selected || function (item) { return false; };
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
gui.define_popup({name:'selection', widget: SelectionPopupWidget});


var TextInputPopupWidget = PopupWidget.extend({
    template: 'TextInputPopupWidget',
    show: function(options){
        options = options || {};
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
gui.define_popup({name:'textinput', widget: TextInputPopupWidget});


var TextAreaPopupWidget = TextInputPopupWidget.extend({
    template: 'TextAreaPopupWidget',
});
gui.define_popup({name:'textarea', widget: TextAreaPopupWidget});

var PackLotLinesRejectedPopupWidget = PopupWidget.extend({
    template: 'PackLotLinesRejectedPopupWidget',
    events: _.extend({}, PopupWidget.prototype.events, {
        'click .cancel': 'click_back',
    }),

    show: function(options){
        this._super(options);
        //this.focus();
    },
    click_confirm: function(){
        this.gui.close_popup();
    },
    click_back: function(){
        //this.pos.gui.show_popup('packlotline', this.options.packlotlinespopup.options);
        this.pos.gui.show_popup('packlotline', {
            'title': _t('Lot/Serial Number(s) Required'),
            'pack_lot_lines': this.options.pack_lot_lines,
            'order_line': this.options.order_line,
            'order': this.options.order,
        });
    },
});
gui.define_popup({name:'packlotlinesrejected', widget: PackLotLinesRejectedPopupWidget});

var PackLotLinePopupWidget = PopupWidget.extend({
    template: 'PackLotLinePopupWidget',
    events: _.extend({}, PopupWidget.prototype.events, {
        'click .remove-lot': 'remove_lot',
        'keydown': 'add_lot',
        'blur .packlot-line-input': 'lose_input_focus'
    }),

    show: function(options){
        this._super(options);
        this.focus();
    },

    click_confirm: function(){

        var self = this;
        var pack_lot_lines = this.options.pack_lot_lines;
        var order_line = this.options.order_line;
        order_line.product.get_lots(this.pos.config.stock_location_id[0]).then(function(db_lots){
            var lot_lines = []
            self.$('.packlot-line-input').each(function(index, el){
                var cid = $(el).attr('cid'),
                    lot_name = $(el).val();
                if (!pack_lot_lines.line_exists(cid, lot_name)) {
                    lot_lines.push({cid: cid, lot_name: lot_name, el: el});
                }
            });
            var lots_nok = order_line.get_invalid_lot_lines(db_lots, lot_lines);
            if (lots_nok.length == 0) {
                self.confirm_and_close(lot_lines);
            } else {
                self.pos.gui.show_popup('packlotlinesrejected', {
                    'title': _t('Lot/Serial-numbers did not match'),
                    'lots_nok': lots_nok,
                    'lot_lines': lot_lines,
                    'order_line': order_line, 
                    'pack_lot_lines': pack_lot_lines,
                    'order': self.options.order,
                });
            }
        });
    },
    confirm_and_close: function(lot_lines) {
        this.options.pack_lot_lines.set_changed_lines(lot_lines);
        this.options.order.save_to_db();
        this.options.order_line.trigger('change', this.options.order_line);
        this.gui.close_popup();
    },
    add_lot: function(ev) {
        var self = this;
        if (ev.keyCode === $.ui.keyCode.ENTER && this.options.order_line.product.tracking == 'serial'){
            this.options.order_line.product.get_lots(this.pos.config.stock_location_id[0]).then(function(db_lots){
                var pack_lot_lines = self.options.pack_lot_lines,
                    cid = $(ev.target).attr('cid'),
                    lot_name = $(ev.target).val();

                var lot_model = pack_lot_lines.get({cid: cid});
                if(!pack_lot_lines.get_empty_model()){
                    var new_lot_model = lot_model.add();
                    self.focus_model = new_lot_model;
                }
                pack_lot_lines.set_quantity_by_lot();
                self.renderElement();
                self.focus();
            });
        }
    },

    remove_lot: function(ev){
        var pack_lot_lines = this.options.pack_lot_lines,
            $input = $(ev.target).prev(),
            cid = $input.attr('cid');
        var lot_model = pack_lot_lines.get({cid: cid});
        lot_model.remove();
        pack_lot_lines.set_quantity_by_lot();
        this.renderElement();
    },

    lose_input_focus: function(ev){
        var $input = $(ev.target),
            cid = $input.attr('cid');
        var lot_model = this.options.pack_lot_lines.get({cid: cid});
        lot_model.set_lot_name($input.val());
    },

    focus: function(){
        this.$("input[autofocus]").focus();
        this.focus_model = false;   // after focus clear focus_model on widget
    }
});
gui.define_popup({name:'packlotline', widget:PackLotLinePopupWidget});

var NumberPopupWidget = PopupWidget.extend({
    template: 'NumberPopupWidget',
    show: function(options){
        options = options || {};
        this._super(options);

        this.inputbuffer = '' + (options.value   || '');
        this.decimal_separator = _t.database.parameters.decimal_point;
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
    click_confirm: function(){
        this.gui.close_popup();
        if( this.options.confirm ){
            this.options.confirm.call(this,this.inputbuffer);
        }
    },
});
gui.define_popup({name:'number', widget: NumberPopupWidget});

var PasswordPopupWidget = NumberPopupWidget.extend({
    renderElement: function(){
        this._super();
        this.$('.popup').addClass('popup-password');
    },
    click_numpad: function(event){
        this._super.apply(this, arguments);
        var $value = this.$('.value');
        $value.text($value.text().replace(/./g, '•'));
    },
});
gui.define_popup({name:'password', widget: PasswordPopupWidget});

var OrderImportPopupWidget = PopupWidget.extend({
    template: 'OrderImportPopupWidget',
});
gui.define_popup({name:'orderimport', widget: OrderImportPopupWidget});

return PopupWidget;
});
