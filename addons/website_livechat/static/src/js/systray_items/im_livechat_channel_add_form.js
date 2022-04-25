/** @odoo-module **/

import FormController from 'web.FormController';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddChannelFormController = FormController.extend({
    /**
     * @override
     */
    saveRecord() {
        return this._super.apply(this, arguments).then(() => {
            const state = this.model.get(this.handle);
            this.do_action({
                type: 'ir.actions.act_window_close',
                infos: { path: state.data.website_url },
            });
        });
    },
});

const AddChannelFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddChannelFormController,
    }),
});

viewRegistry.add('website_livechat_add_form', AddChannelFormView);

export default {
    AddChannelFormController: AddChannelFormController,
    AddChannelFormView: AddChannelFormView,
};
