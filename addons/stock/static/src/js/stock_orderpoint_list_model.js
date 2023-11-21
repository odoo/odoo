odoo.define('stock.StockOrderpointListModel', function (require) {
"use strict";

var core = require('web.core');
var ListModel = require('web.ListModel');

var qweb = core.qweb;


var StockOrderpointListModel = ListModel.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------
    /**
     */
    replenish: function (recordResIds) {
      var self = this;
      return this._rpc({
          model: this.loadParams.modelName,
          method: 'action_replenish',
          args: [recordResIds],
          context: this.loadParams.context,
      }).then(function () {
          return self.do_action('stock.action_replenishment');
      });
    },

    snooze: function (recordResIds) {
      var self = this;
      return this.do_action('stock.action_orderpoint_snooze', {
          additional_context: {
              default_orderpoint_ids: recordResIds
          },
          on_close: () => self.do_action('stock.action_replenishment')
      });
    },
});

return StockOrderpointListModel;

});
