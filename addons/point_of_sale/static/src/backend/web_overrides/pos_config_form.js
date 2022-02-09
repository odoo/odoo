odoo.define('point_of_sale.pos_config_form', function (require) {
    'use strict';

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var rpc = require('web.rpc');

    var PosConfigFormController = FormController.extend({
        saveRecord: async function (recordID) {
            const _super = this._super;
            const record = this.model.localData[recordID || this.handle];
            const fieldsToChange = Object.keys(
                this.model._generateChanges(record, { viewType: undefined, changesOnly: true })
            );
            let shouldReload = false;
            if (fieldsToChange.length) {
                shouldReload = await rpc.query(
                    rpc.buildQuery({
                        model: 'pos.config',
                        method: 'are_there_uninstalled_modules',
                        args: [fieldsToChange],
                    })
                );
            }
            const result = await _super.apply(this, arguments);
            if (shouldReload) {
                window.location.reload();
            }
            return result;
        },
    });

    var PosConfigFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: PosConfigFormController,
        }),
    });

    viewRegistry.add('pos_config_form', PosConfigFormView);
    return FormView;
});
