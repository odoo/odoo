odoo.define('data_recycle.CommonListController', function (require) {
"use strict";

    var ListController = require('web.ListController');

    var DataCommonListController = ListController.extend({
        /**
         * Open the form view of the original record, and not the data_merge.record view
         * @override
         */
        _onOpenRecord: function(event) {
            var record = this.model.get(event.data.id, {raw: true});

            this.do_action({
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
                res_model: record.data.res_model_name,
                res_id: record.data.res_id,
                context: {
                    create: false,
                    edit: false
                }
            });
        },

        /**
         * Render the "Merge" & "Unselect" buttons when records are selected
         * @override
         */
        _updateControlPanel: function() {
            this._super.apply(this, arguments);

            if(this.selectedRecords.length > 0) {
                $('.o_list_buttons').removeClass('d-none');
            } else {
                $('.o_list_buttons').addClass('d-none');
            }
        },

        /**
         * Unselect all the records
         * @param {*} ev
         */
        _onUnselectClick: function(ev) {
            this.renderer._onToggleSelection(ev);
        },
    });

    return DataCommonListController;
});
