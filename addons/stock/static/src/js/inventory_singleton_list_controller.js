odoo.define('stock.SingletonListController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');

var _t = core._t;


var SingletonListController = ListController.extend({
    _confirmSave: function (id) {
        var newRecord = this.model.localData[id];
        var model = newRecord.model;
        var res_id = newRecord.res_id;
        var data = this.model.get(this.handle).data;
        var foundedRecords = _.filter(data, function (rec) {
            return rec.res_id === res_id && rec.model === model;
        });
        if (foundedRecords.length > 1) {
            var self = this;
            var prom = this.reload();
            prom.then(function () {
                var notification = _t("You tried to create a record who already exists."+
                "<br/>This last one has been modified instead.");
                self.do_notify(_t("This record already exists."), notification);
                var $td = $('.o_list_view tr.o_data_row:first-child td');
                var fieldIndex = Math.max($td.length - 2, 0);
                self.renderer._selectCell(0, fieldIndex);
            });
            return prom;
        }
        else return this._super(id);
    },
});

return SingletonListController;

});
