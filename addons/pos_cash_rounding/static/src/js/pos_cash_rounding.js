odoo.define('pos_cash_rounding.cash_rounding', function (require) {
    "use strict";

var models = require('point_of_sale.models');
var rpc = require('web.rpc');
var screens = require('point_of_sale.screens');
var utils = require('web.utils');

var round_pr = utils.round_precision;


models.load_models([{
    model: 'account.cash.rounding',
    fields: ['name', 'rounding', 'rounding_method'],
    domain: function(self){return [['id', '=', self.config.rounding_method[0]]]; },
    loaded: function(self, cash_rounding) {
        self.cash_rounding = cash_rounding;
    }
},
]);

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    export_for_printing: function() {
      var result = _super_order.export_for_printing.apply(this,arguments);
      result.total_rounded = this.get_total_with_tax() + this.get_rounding_applied();
      result.rounding_applied = this.get_rounding_applied();
      return result;
    },
    get_due: function(paymentline) {
      var due  = _super_order.get_due.apply(this, arguments);
      due += this.get_rounding_applied();
      return round_pr(due, this.pos.currency.rounding);
    },
    get_change_value: function(paymentline) {
      var change  = _super_order.get_change_value.apply(this, arguments);
      change -= this.get_rounding_applied();
      return round_pr(change, this.pos.currency.rounding);
    },
    get_rounding_applied: function() {
        if(this.pos.config.cash_rounding) {
            var total = round_pr(this.get_total_with_tax(), this.pos.cash_rounding[0].rounding);

            var rounding_applied = total - this.get_total_with_tax();
            // because floor and ceil doesn't include decimals in calculation, we reuse the value of the half-up and adapt it.
            if(this.pos.cash_rounding[0].rounding_method === "UP" && rounding_applied < 0) {
                rounding_applied += this.pos.cash_rounding[0].rounding;
            }
            else if(this.pos.cash_rounding[0].rounding_method === "DOWN" && rounding_applied > 0){
                rounding_applied -= this.pos.cash_rounding[0].rounding;
            }
            return rounding_applied;
        }
        return 0;
    },
});
});
