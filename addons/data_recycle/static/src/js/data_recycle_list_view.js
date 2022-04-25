odoo.define('data_recycle.ListView', function (require) {
"use strict";

    var ListView = require('web.ListView');
    var session = require('web.session');
    var viewRegistry = require('web.view_registry');
    var DataCommonListController = require('data_recycle.CommonListController');

    var DataCleaningListController = DataCommonListController.extend({
        buttons_template: 'DataRecycle.buttons',
        /**
         * @override
         */
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            this.$buttons.on('click', '.o_data_recycle_validate_button', this._onValidateClick.bind(this));
            this.$buttons.on('click', '.o_data_recycle_unselect_button', this._onUnselectClick.bind(this));
        },

        /**
         * Validate all the records selected
         * @param {*} ev
         */
        _onValidateClick: async function(ev) {
            const self = this;
            const state = this.model.get(this.handle);
            let record_ids;
            if (this.isDomainSelected) {
                record_ids = await this._domainToResIds(state.getDomain(), session.active_ids_limit);
            } else {
                record_ids = this.getSelectedIds();
            }

            this._rpc({
                model: 'data_recycle.record',
                method: 'action_validate',
                args: [record_ids],
            }).then(function(data) {
                self.trigger_up('reload');
            });
        },
    });

    var DataCleaningListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: DataCleaningListController,
        }),
    });

    viewRegistry.add('data_recycle_list', DataCleaningListView);
});
