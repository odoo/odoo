odoo.define('point_of_sale.BaseWidget', function (require) {
"use strict";

var Widget = require('web.Widget');

// This is a base class for all Widgets in the POS. It exposes relevant data to the 
// templates : 
// - widget.currency : { symbol: '$' | '€' | ..., position: 'before' | 'after }
// - widget.format_currency(amount) : this method returns a formatted string based on the
//   symbol, the position, and the amount of money.
// if the PoS is not fully loaded when you instanciate the widget, the currency might not
// yet have been initialized. Use __build_currency_template() to recompute with correct values
// before rendering.
var PosBaseWidget = Widget.extend({
    init:function(parent,options){
        this._super(parent);
        options = options || {};
        this.pos    = options.pos    || (parent ? parent.pos : undefined);
        this.chrome = options.chrome || (parent ? parent.chrome : undefined);
        this.gui    = options.gui    || (parent ? parent.gui : undefined); 

        // the widget class does not support anymore using $el/el before the
        // 'start' lifecycle method, but point of sale actually needs it.
        this.setElement(this._makeDescriptive());
    },
    format_currency: function(amount,precision) {
        return this.pos.format_currency(amount, precision);
    },
    format_currency_no_symbol: function(amount, precision) {
        return this.pos.format_currency_no_symbol(amount, precision);
    },
    show: function(){
        this.$el.removeClass('oe_hidden');
    },
    hide: function(){
        this.$el.addClass('oe_hidden');
    },
    format_pr: function(value,precision){
        return this.pos.format_pr(value, precision);
    },
    format_fixed: function(value,integer_width,decimal_width){
        value = value.toFixed(decimal_width || 0);
        var width = value.indexOf('.');
        if (width < 0 ) {
            width = value.length;
        }
        var missing = integer_width - width;
        while (missing > 0) {
            value = '0' + value;
            missing--;
        }
        return value;
    },
});

return PosBaseWidget;

});
