import {NewContentFormController, NewContentFormView} from '@website/js/new_content_form';
import {registry} from "@web/core/registry";

export class AddForumFormController extends NewContentFormController {
    /**
     * @override
     */
    computePath() {
        return `/forum/${encodeURIComponent(this.model.root.resId)}`;
    }
}

export const AddForumFormView = {
    ...NewContentFormView,
    Controller: AddForumFormController,
};

registry.category("views").add("website_forum_add_form", AddForumFormView);
