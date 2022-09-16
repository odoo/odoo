/** @odoo-module **/

import {formView} from "@web/views/form/form_view";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";

export class NewContentFormController extends formView.Controller {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.action = useService('action');
    }

    /**
     * @override
     */
    async save() {
        await super.save();
        if (this.model.root.resId) {
            this.action.doAction({
                type: 'ir.actions.act_window_close',
                infos: {path: this.path},
            });
        }
    }

    /**
     * Returns the URL to redirect to once the website content (blog, etc)
     * record is created.
     * Override this getter to get the correct path for records without
     * 'website_url' field.
     *
     * @returns {String}
     */
    get path() {
        return this.model.root.data.website_url;
    }
}

export const NewContentFormView = {
    ...formView,
    display: {controlPanel: false},
    Controller: NewContentFormController,
};

registry.category("views").add("website_new_content_form", NewContentFormView);
