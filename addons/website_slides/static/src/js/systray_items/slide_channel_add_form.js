/** @odoo-module **/

import {NewContentFormController} from '@website/js/new_content_form';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddCourseFormController = NewContentFormController.extend({
    /**
     * @override
     */
    _getPath(state) {
        return `/slides/${state.data.id}`;
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
