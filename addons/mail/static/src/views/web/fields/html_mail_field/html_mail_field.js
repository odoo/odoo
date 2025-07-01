import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { getCSSRules, toInline } from "./convert_inline";
import { ColumnPlugin } from "@html_editor/main/column_plugin";

const cssRulesByDocument = new WeakMap();

export class HtmlMailField extends HtmlField {
    /**
     * @param {HTMLElement} el element to be processed
     * @param {Object[]} cssRules result of @see getCSSRules
     */
    static async getInlineHTML(el, cssRules) {
        // Insert the cloned element inside an DOM so we can get its computed style.
        previousSibling.after(el);
        el.classList.remove("odoo-editor-editable");
        await toInline(el, cssRules);
        el.remove();
        return el;
    }

    async getEditorContent() {
        let el = await super.getEditorContent();
        el = await this.processEditorContent(el);
        return el;
    }

    async processEditorContent(el) {
        const editable = this.editor.editable;
        const editableDocument = editable.ownerDocument;
        if (!cssRulesByDocument.has(editableDocument)) {
            cssRulesByDocument.set(editableDocument, getCSSRules(editableDocument));
        }
        const cssRules = cssRulesByDocument.get(previousSibling);
        return await HtmlMailField.getInlineHTML(el, cssRules);
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
    extractProps({ attrs, options }, dynamicInfo) {
        const props = htmlField.extractProps({ attrs, options }, dynamicInfo);
        props.embeddedComponents = false;
        return props;
    },
};

registry.category("fields").add("html_mail", htmlMailField);
