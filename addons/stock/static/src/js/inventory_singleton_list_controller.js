odoo.define('stock.SingletonListController', function (require) {
"use strict";

var core = require('web.core');
var InventoryReportListController = require('stock.InventoryReportListController');

var _t = core._t;

/**
 * The purpose of this override has 2 purposes:
 *
 * 1. Avoid having two or more similar records in the list view.
 *    It is expected to be used in quant list views, when the list is editable
 *    and allows new line creation. Checks for whether newly created quant
 *    already exists and if it does => update the existing quant instead of the
 *    newly created one, and then we refresh the view to avoid having 2 similar lines.
 *
 * 2. Support Inventory Adjustments (i.e. inventory counts) view.
 *    Specifically adds necessary buttons (or hides them when appropriate) and
 *    autosaving logic to prevent button actions before edits are saved.
 */

var SingletonListController = InventoryReportListController.extend({
    buttons_template: 'StockQuant.Buttons',

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------
    /**
     * @override
     */
    renderButtons: function ($node) {
        this._super.apply(this, arguments);
        this.$buttons.on('click', '.o_button_apply_inventory', this._onApplyInventory.bind(this));
        this.$buttons.on('click', '.o_button_request_count_inventory', this._onRequestCountInventory.bind(this));
        this.$buttons.on('click', '.o_button_set_inventory', this._onSetInventory.bind(this));
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * @override
     * @return {Promise} rejected when updating the list because we don't want
     * to select a cell that might not exist anymore.
     */
    _confirmSave: function (id) {
        var newRecord = this.model.localData[id];
        var model = newRecord.model;
        var res_id = newRecord.res_id;

        var findSimilarRecords = function (record) {
            if ((record.groupedBy && record.groupedBy.length > 0) || record.data.length) {
                var recordsToReturn = [];
                for (var i in record.data) {
                    var foundRecords = findSimilarRecords(record.data[i]);
                    recordsToReturn = recordsToReturn.concat(foundRecords || []);
                }
                return recordsToReturn;
            } else {
                if (record.res_id === res_id && record.model === model) {
                    if (record.count === 0){
                        return [record];
                    }
                    else if (record.ref && record.ref.indexOf('virtual') !== -1) {
                        return [record];
                    }
                }
            }
        };

        var handle = this.model.get(this.handle);
        var similarRecords = findSimilarRecords(handle);

        if (similarRecords.length > 1) {
            var notification = _t("You tried to create a record that already exists."+
            "<br/>The existing record has been modified instead.");
            this.do_notify(_t("This record already exists."), notification);
            this.reload();
            return Promise.reject();
        }
        else {
            return this._super.apply(this, arguments);
        }
    },

    /**
     * Override to show/hide inventory adjustment specific buttons.
     * Maybe a bit too hacky since it's not the intended purpose of this function,
     * but for some reason `_updateControlPanel` isn't called during reload action
     * after triggering any of these buttons.
     *
     * @override
     */
    _renderHeaderButtons() {
        this._super.apply(this, arguments);

        if (this.selectedRecords.length > 0 && !this.context.inventory_report_mode) {
            $('.o_button_apply_inventory').removeClass('d-none');
            $('.o_button_request_count_inventory').removeClass('d-none');
            $('.o_button_set_inventory').removeClass('d-none');
        } else {
            $('.o_button_apply_inventory').addClass('d-none');
            $('.o_button_request_count_inventory').addClass('d-none');
            $('.o_button_set_inventory').addClass('d-none');
        }
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    _onApplyInventory: function (ev) {
        var self = this;
        var ids = this.getSelectedIds();
        if (!ids.length) {
            var modified_records = this.initialState.data.filter(record => record.data.inventory_diff_quantity != 0)
            ids = modified_records.map(record => record.data.id)
        }
        if (ids.length) {
            return this._rpc({
                model: 'stock.quant',
                method: 'action_apply_inventory',
                args: [ids],
                context: this.context,
            }).then((result) => {
                if (!result) {
                    return self.trigger_up('reload');
                }
                return self.do_action(result, {on_close: () => this.reload(),});
            })
        }
    },

    /**
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onButtonClicked: function (ev) {
        ev.stopPropagation();
        var self = this;
        return self.saveRecord(ev.data.record.id, {
            stayInEdit: true,
        }).then(function () {
            // we need to re-get the record to make sure we have changes made
            // by the basic model, such as the new res_id, if the record is
            // new.
            var record = self.model.get(ev.data.record.id);
            return self._callButtonAction(ev.data.attrs, record);
        }).then(function () {
            self._enableButtons();
        }).guardedCatch(this._enableButtons.bind(this));
    },

    _onRequestCountInventory: function (ev) {
        var ids = this.getSelectedIds();
        if ( ids.length ) {
            return this.do_action('stock.action_stock_request_count',
            {
                additional_context: {
                        default_quant_ids: ids,
                },
                on_close: () => this.reload(),
            });
        }
    },

    _onSetInventory: function (ev) {
        var self = this;
        var ids = this.getSelectedIds();
        if (ids.length) {
            return this._rpc({
                model: 'stock.quant',
                method: 'action_set_inventory_quantity',
                args: [ids],
                context: this.context,
            }).then(() => {
                return self.trigger_up('reload');
            });
        }
    },
});

return SingletonListController;

});
