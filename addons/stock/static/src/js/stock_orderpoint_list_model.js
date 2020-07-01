odoo.define('stock.StockOrderpointListModel', function (require) {
"use strict";

var core = require('web.core');
var ListModel = require('web.ListModel');

var qweb = core.qweb;

var today = new Date().toJSON().slice(0,10);
var lead_days_date = new Date();
lead_days_date.setDate(lead_days_date.getDate() + 5)
lead_days_date = lead_days_date.toJSON().slice(0,10);
const EXAMPLES = [{
    id: 0,
    trigger: 'manual',
    product_id: [0, "[E-COM09] Large Desk"],
    location_id: [0, "WH/Stock"],
    route_id: [0, "Buy"],
    product_min_qty: 0.0,
    product_max_qty: 0.0,
    qty_on_hand: 0.0,
    qty_forecast: -5.0,
    json_lead_days_popover: _.str.sprintf('{"title": "Replenishment", "popoverTemplate": "stock.leadDaysPopOver", "lead_days_date": "%s", "today": "%s", "trigger": "manual", "qty_forecast": -5.0, "qty_to_order": 5.0, "product_min_qty": 0.0, "product_max_qty": 0.0, "product_uom_name": "Units", "virtual": false, "lead_days_description": "<tr><td>Vendor Lead Time</td><td class=\'text-right\'>+ 5 day(s)</td></tr><tr><td>Purchase Security Lead Time</td><td class=\'text-right\'>+ 0 day(s)</td></tr><tr><td>Days to Purchase</td><td class=\'text-right\'>+ 0 day(s)</td></tr>"}', lead_days_date, today),
    qty_to_order: 5.0,
}, {
    id: 1,
    trigger: 'manual',
    product_id: [0, "[FURN_2333] Table Leg"],
    location_id: [0, "WH/Stock"],
    route_id: [0, "Buy"],
    product_min_qty: 0.0,
    product_max_qty: 10.0,
    qty_on_hand: 0.0,
    qty_forecast: -5.0,
    json_lead_days_popover: _.str.sprintf('{"title": "Replenishment", "popoverTemplate": "stock.leadDaysPopOver", "lead_days_date": "%s", "today": "%s", "trigger": "manual", "qty_forecast": -5.0, "qty_to_order": 15.0, "product_min_qty": 0.0, "product_max_qty": 10.0, "product_uom_name": "Units", "virtual": false, "lead_days_description": "<tr><td>Vendor Lead Time</td><td class=\'text-right\'>+ 5 day(s)</td></tr><tr><td>Purchase Security Lead Time</td><td class=\'text-right\'>+ 0 day(s)</td></tr><tr><td>Days to Purchase</td><td class=\'text-right\'>+ 0 day(s)</td></tr>"}', lead_days_date, today),
    qty_to_order: 15.0,
}, {
    id: 2,
    trigger: 'manual',
    product_id: [0, "[FURN_8900] Drawer Black"],
    location_id: [0, "WH/Stock"],
    route_id: [0, "Buy"],
    product_min_qty: 10.0,
    product_max_qty: 20.0,
    qty_on_hand: 5.0,
    qty_forecast: 5.0,
    json_lead_days_popover: _.str.sprintf('{"title": "Replenishment", "popoverTemplate": "stock.leadDaysPopOver", "lead_days_date": "%s", "today": "%s", "trigger": "manual", "qty_forecast": 5.0, "qty_to_order": 15.0, "product_min_qty": 10.0, "product_max_qty": 20.0, "product_uom_name": "Units", "virtual": false, "lead_days_description": "<tr><td>Vendor Lead Time</td><td class=\'text-right\'>+ 5 day(s)</td></tr><tr><td>Purchase Security Lead Time</td><td class=\'text-right\'>+ 0 day(s)</td></tr><tr><td>Days to Purchase</td><td class=\'text-right\'>+ 0 day(s)</td></tr>"}', lead_days_date, today),
    qty_to_order: 15.0,
}, {
    id: 3,
    trigger: 'manual',
    product_id: [0, "[FURN_8522] Table Top"],
    location_id: [0, "WH/Stock/Shelf1"],
    route_id: [0, "Manufacture"],
    product_min_qty: 0.0,
    product_max_qty: 0.0,
    qty_on_hand: 0.0,
    qty_forecast: -2.0,
    json_lead_days_popover: _.str.sprintf('{"title": "Replenishment", "popoverTemplate": "stock.leadDaysPopOver", "lead_days_date": "%s", "today": "%s", "trigger": "manual", "qty_forecast": -2.0, "qty_to_order": 2.0, "product_min_qty": 0.0, "product_max_qty": 0.0, "product_uom_name": "Units", "virtual": false, "lead_days_description": "<tr><td>Vendor Lead Time</td><td class=\'text-right\'>+ 5 day(s)</td></tr><tr><td>Purchase Security Lead Time</td><td class=\'text-right\'>+ 0 day(s)</td></tr><tr><td>Days to Purchase</td><td class=\'text-right\'>+ 0 day(s)</td></tr>"}', lead_days_date, today),
    qty_to_order: 2.0,
}];

var StockOrderpointListModel = ListModel.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------
    /**
     * @override
     */
    get(_, options) {
        let state = this._super(...arguments);
        if (state.isSample) {
            state.data = state.data.slice(0, 4);
            state.count = 4;
            for (var i = 0; i < 4; i++) {
                state.data[i].data = Object.assign(state.data[i].data, EXAMPLES[i]);
            }
        }
        return state;
    },

    /**
     */
    replenish: function (records) {
      var self = this;
      var model = records[0].model;
      var recordResIds = _.pluck(records, 'res_id');
      var context = records[0].getContext();
      return this._rpc({
          model: model,
          method: 'action_replenish',
          args: [recordResIds],
          context: context,
      }).then(function () {
          return self.do_action('stock.action_replenishment');
      });
    },

    snooze: function (records) {
      var recordResIds = _.pluck(records, 'res_id');
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
