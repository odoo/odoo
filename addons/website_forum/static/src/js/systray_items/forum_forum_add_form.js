/** @odoo-module **/

import FormController from 'web.FormController';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddForumFormController = FormController.extend({
    /**
     * @override
     */
    saveRecord() {
        return this._super.apply(this, arguments).then(() => {
            const state = this.model.get(this.handle);
            this.do_action({
                type: 'ir.actions.act_window_close',
                infos: { path: `/forum/${state.data.id}` },
            });
        });
    },
});

const AddForumFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddForumFormController,
    }),
});

viewRegistry.add('website_forum_add_form', AddForumFormView);

export default {
    AddForumFormController: AddForumFormController,
    AddForumFormView: AddForumFormView,
};
