/** @odoo-module **/

import { HtmlField, htmlField } from "@web_editor/js/backend/html_field";
import { registry } from "@web/core/registry";

/**
 * Plugin for OdooEditor. Allow to prevent creating attachments for added images in description field.
 */
export class ProjectSharingPlugin {
    constructor ({ editor }) {
        this.editor = editor;
    }
    /**
     * Retrieve all the <img> in the field and remove the class "o_b64_image_to_save"
     * to prevent creating attachments for those images.
     */
    cleanForSave() {
        for (const image of this.editor.editable.querySelectorAll('img')) {
            image.classList.remove('o_b64_image_to_save');
        }
    }
}

export class ProjectSharingHtmlField extends HtmlField {
    get wysiwygOptions() {
        const wysiwygOptions = super.wysiwygOptions;
        wysiwygOptions.editorPlugins = [wysiwygOptions.editorPlugins, ProjectSharingPlugin].flat();
        return wysiwygOptions;
    }
}

export const projectSharingHtmlField = {
    ...htmlField,
    component: ProjectSharingHtmlField,
};

registry.category("fields").add("project_sharing_html", projectSharingHtmlField);
