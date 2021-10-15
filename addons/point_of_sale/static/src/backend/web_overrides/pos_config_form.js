odoo.define('point_of_sale.pos_config_form', function (require) {
    'use strict';

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var PosConfigFormController = FormController.extend({
        _enableButtons: function (changedFields) {
            let shouldReload = false;
            if (Array.isArray(changedFields)) {
                for (let field of (changedFields)) {
                    if (
                        field.startsWith('module_') ||
                        field.startsWith('group_') ||
                        field === 'is_posbox'
                    ) {
                        shouldReload = true;
                        break;
                    }
                }
            }
            if (shouldReload) {
                window.location.reload();
            } else {
                this._super.apply(this, arguments);
            }
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
