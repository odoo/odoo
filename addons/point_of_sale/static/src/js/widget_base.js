odoo.define('point_of_sale.BaseWidget', function (require) {
"use strict";

var formats = require('web.formats');
var utils = require('web.utils');
var Widget = require('web.Widget');

var round_di = utils.round_decimals;

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
    },
    format_currency: function(amount,precision){
        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};

        amount = this.format_currency_no_symbol(amount,precision);

        if (currency.position === 'after') {
            return amount + ' ' + (currency.symbol || '');
        } else {
            return (currency.symbol || '') + ' ' + amount;
        }
    },
    format_currency_no_symbol: function(amount, precision) {
        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
        var decimals = currency.decimals;

        if (precision && (typeof this.pos.dp[precision]) !== undefined) {
            decimals = this.pos.dp[precision];
        }

        if (typeof amount === 'number') {
            amount = round_di(amount,decimals).toFixed(decimals);
            amount = formats.format_value(round_di(amount, decimals), { type: 'float', digits: [69, decimals]});
        }

        return amount;
    },
    show: function(){
        this.$el.removeClass('oe_hidden');
    },
    hide: function(){
        this.$el.addClass('oe_hidden');
    },
    format_pr: function(value,precision){
        var decimals = precision > 0 ? Math.max(0,Math.ceil(Math.log(1.0/precision) / Math.log(10))) : 0;
        return value.toFixed(decimals);
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
