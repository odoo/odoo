/** @odoo-module**/

import FormController from 'web.FormController';
import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';


const PickingFormController = FormController.extend({
    /**
     * @override
     */
     init: function () {
        this._super(...arguments);
        this.hasActionMenus = false;
    },
});

const PickingFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: PickingFormController,
    }),
});

viewRegistry.add('subcontracting_portal_picking_form_view', PickingFormView);

export default {
    PickingFormView: PickingFormView,
    PickingFormController: PickingFormController
};
