/** @odoo-module **/

import FormController from 'web.FormController';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddCourseFormController = FormController.extend({
    /**
     * @override
     */
    saveRecord() {
        return this._super.apply(this, arguments).then(() => {
            const state = this.model.get(this.handle);
            this.do_action({
                type: 'ir.actions.act_window_close',
                infos: { path: `/slides/${state.data.id}` },
            });
        });
    },
});

const AddCourseFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AddCourseFormController,
    }),
});

viewRegistry.add('website_slides_add_form', AddCourseFormView);

export default {
    AddCourseFormController: AddCourseFormController,
    AddCourseFormView: AddCourseFormView,
};
