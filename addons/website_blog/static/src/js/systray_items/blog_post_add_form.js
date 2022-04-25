/** @odoo-module **/

import FormController from 'web.FormController';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddBlogFormController = FormController.extend({
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

const AddBlogFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddBlogFormController,
    }),
});

viewRegistry.add('website_blog_add_form', AddBlogFormView);

export default {
    AddBlogFormController: AddBlogFormController,
    AddBlogFormView: AddBlogFormView,
};
