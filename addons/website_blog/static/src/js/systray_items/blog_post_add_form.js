/** @odoo-module **/

import {NewContentFormController} from '@website/js/new_content_form';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

export const AddBlogFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: NewContentFormController,
    }),
});

viewRegistry.add('website_blog_add_form', AddBlogFormView);
