/** @odoo-module **/

import {NewContentFormController, NewContentFormView} from '@website/js/new_content_form';
import {registry} from "@web/core/registry";

export class AddForumFormController extends NewContentFormController {
    /**
     * @override
     */
    get path() {
        return `/forum/${this.model.root.data.id}`;
    }
}

export const AddForumFormView = {
    ...NewContentFormView,
    Controller: AddForumFormController,
};

registry.category("views").add("website_forum_add_form", AddForumFormView);
