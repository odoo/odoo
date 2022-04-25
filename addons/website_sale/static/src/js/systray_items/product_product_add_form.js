/** @odoo-module **/

import FormController from 'web.FormController';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddProductFormController = FormController.extend({
    saveRecord() {
        return this._super.apply(this, arguments).then(() => {
            const state = this.model.get(this.handle);
            this.do_action({
                type: 'ir.actions.act_window_close',
                infos: { path: `${state.data.website_url.split('#')[0]}?enable_editor=1` },
            });
        });
    },
});

const AddProductFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddProductFormController,
    }),
});

viewRegistry.add('product_product_add_form', AddProductFormView);

export default {
    AddProductFormController: AddProductFormController,
    AddProductFormView: AddProductFormView,
};
