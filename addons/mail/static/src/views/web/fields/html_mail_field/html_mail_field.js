import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { getCSSRules, toInline } from "./convert_inline";
import { ColumnPlugin } from "@html_editor/main/column_plugin";

const cssRulesByElement = new WeakMap();

export class HtmlMailField extends HtmlField {
    /**
     * @param {WeakMap} cssRulesByElement
     * @param {Editor} editor
     * @param {HTMLElement} el
     */
    static async getInlinedEditorContent(cssRulesByElement, editor, el) {
        if (!cssRulesByElement.has(editor.editable)) {
            cssRulesByElement.set(editor.editable, getCSSRules(editor.document));
        }
        const cssRules = cssRulesByElement.get(editor.editable);
        el.classList.remove("odoo-editor-editable");
        await toInline(el, cssRules);
    }

    async getEditorContent() {
        const el = await super.getEditorContent();
        await HtmlMailField.getInlinedEditorContent(cssRulesByElement, this.editor, el);
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
