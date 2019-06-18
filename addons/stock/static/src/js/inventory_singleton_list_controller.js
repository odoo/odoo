odoo.define('stock.SingletonListController', function (require) {
"use strict";

var core = require('web.core');
var InventoryReportListController = require('stock.InventoryReportListController');

var _t = core._t;

/**
 * The purpose of this override is to avoid to have two or more similar records
 * in the list view.
 *
 * It's used in quant list view, a list editable where when you create a new
 * line about a quant who already exists, we want to update the existing one
 * instead of create a new one, and then we don't want to have two similar line
 * in the list view, so we refresh it.
 */

var SingletonListController = InventoryReportListController.extend({
    /**
     * @override
     * @return {Promise} rejected when update the list because we don't want
     * anymore to select a cell who maybe doesn't exist anymore.
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
            var notification = _t("You tried to create a record who already exists."+
            "<br/>This last one has been modified instead.");
            this.do_notify(_t("This record already exists."), notification);
            this.reload();
            return Promise.reject();
        }
        else {
            return this._super.apply(this, arguments);
        }
    },
});

return SingletonListController;

});
