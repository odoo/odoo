/** @odoo-module **/

import {NewContentFormController} from '@website/js/new_content_form';
import viewRegistry from 'web.view_registry';
import FormView from 'web.FormView';

const AddForumFormController = NewContentFormController.extend({
    /**
     * @override
     */
    _getPath(state) {
        return `/forum/${state.data.id}`;
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
