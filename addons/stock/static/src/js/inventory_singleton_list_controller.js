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
            var notification = _t("You have tried to create a record which already exists. " +
            "The existing record has been modified instead.");
            this.displayNotification({ title: _t("This record already exists."), message: notification });
            this.reload();
            return Promise.reject();
        }
        else {
            return this._super.apply(this, arguments);
        }
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

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
});

return SingletonListController;

});
