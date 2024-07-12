import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { getCSSRules, toInline } from "./convert_inline";
import { ColumnPlugin } from "@html_editor/main/column_plugin";

const cssRulesByElement = new WeakMap();

export class HtmlMailField extends HtmlField {
    async getEditorContent() {
        if (!cssRulesByElement.has(this.editor.editable)) {
            cssRulesByElement.set(this.editor.editable, getCSSRules(this.editor.document));
        }
        const cssRules = cssRulesByElement.get(this.editor.editable);
        const el = await super.getEditorContent();
        el.classList.remove("odoo-editor-editable");
        await toInline(el, cssRules);
        return el;
    }

    getConfig() {
        const config = super.getConfig();
        config.dropImageAsAttachment = false;
        config.Plugins = config.Plugins.filter((plugin) => plugin !== ColumnPlugin);
        return config;
    }
}

export const htmlMailField = {
    ...htmlField,
    component: HtmlMailField,
    additionalClasses: ["o_field_html"],
};

registry.category("fields").add("html_mail", htmlMailField);
