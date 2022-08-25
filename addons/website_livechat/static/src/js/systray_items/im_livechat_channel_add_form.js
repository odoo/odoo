/** @odoo-module **/

import {NewContentFormController} from '@website/js/new_content_form';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

export const AddChannelFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: NewContentFormController,
    }),
});

viewRegistry.add('website_livechat_add_form', AddChannelFormView);
