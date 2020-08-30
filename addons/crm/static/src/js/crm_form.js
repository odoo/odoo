odoo.define("crm.crm_form", function (require) {
    "use strict";

    /**
     * This From Controller makes sure we display a rainbowman message
     * when the stage is won, even when we click on the statusbar.
     * When the stage of a lead is changed and data are saved, we check
     * if the lead is won and if a message should be displayed to the user
     * with a rainbowman like when the user click on the button "Mark Won".
     */

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var CrmFormController = FormController.extend({
        /**
         * After data are saved we display a possible rainbowman
         * message when the stage is won.
         * @override
         */
        _applyChanges: async function (dataPointID, changes, event) {
            var result = await this._super(...arguments);
            if ('stage_id' in changes) {
                const message = await this._rpc({
                    model: 'crm.lead',
                    method : 'get_rainbowman_message',
                    args: [[parseInt(event.target.res_id)]],
                });
                if (message) {
                    this.trigger_up('show_effect', {
                        message: message,
                        type: 'rainbow_man',
                    });
                }
            }
            return result;
        },
    });

    var CrmFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: CrmFormController,
        }),
    });

    viewRegistry.add('crm_form', CrmFormView);

    return {
        CrmFormController: CrmFormController,
        CrmFormView: CrmFormView,
    };
});
