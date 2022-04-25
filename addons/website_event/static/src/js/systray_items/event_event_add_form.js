/** @odoo-module **/

import FormController from 'web.FormController';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddEventFormController = FormController.extend({
    /**
     * @override
     */
    saveRecord() {
        return this._super.apply(this, arguments).then(() => {
            const state = this.model.get(this.handle);
            this.do_action({
                type: 'ir.actions.act_window_close',
                infos: { path: `${state.data.website_url}?enable_editor=1` },
            });
        });
    },
});

const AddEventFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddEventFormController,
    }),
});

viewRegistry.add('event_event_add_form', AddEventFormView);

export default {
    AddEventFormController: AddEventFormController,
    AddEventFormView: AddEventFormView,
};
