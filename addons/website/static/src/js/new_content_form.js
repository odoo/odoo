/** @odoo-module **/

import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";

export class NewContentFormController extends formView.Controller {
    /**
     * @override
     */
    async save() {
        return super.save({ computePath: () => this.computePath(), ...arguments });
    }

    /**
     * Returns the URL to redirect to once the website content (blog, etc)
     * record is created.
     * Override this method to get the correct path for records without
     * 'website_url' field.
     *
     * @returns {String}
     */
    computePath() {
        return this.model.root.data.website_url;
    }
}

export const NewContentFormView = {
    ...formView,
    display: {controlPanel: false},
    Controller: NewContentFormController,
};

registry.category("views").add("website_new_content_form", NewContentFormView);
