import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { getCSSRules, toInline } from "./convert_inline";
import { ColumnPlugin } from "@html_editor/main/column_plugin";

const cssRulesByDocument = new WeakMap();

export class HtmlMailField extends HtmlField {
    setup() {
        super.setup();
        this.alwaysComputeInlineEditorContent = true;
    }

    /**
     * @param {HTMLElement} el element to be processed
     * @param {Document} styleDocument source document for the style
     */
    // TODO EGGMAIL: rename this as it returns an ELEMENT not html
    static async getInlineHTML(el, styleDocument) {
        if (!cssRulesByDocument.has(styleDocument)) {
            cssRulesByDocument.set(styleDocument, getCSSRules(styleDocument));
        }
        const cssRules = cssRulesByDocument.get(styleDocument);
        await toInline(el, cssRules);
        return el;
    }

    async getEditorContent() {
        if (this.alwaysComputeInlineEditorContent) {
            return this.getInlineEditorContent();
        }
        return super.getEditorContent();
    }

    /**
     * Temporarily insert the cloned element inside the DOM so we can get its computed style.
     * @param {HTMLElement} el
     */
    insertForInlineProcessing(el) {
        const editable = this.editor.editable;
        editable.after(el);
    }

    async getInlineEditorContent() {
        let el = await super.getEditorContent();
        el.classList.remove("odoo-editor-editable");
        const editable = this.editor.editable;
        const editableDocument = editable.ownerDocument;
        this.insertForInlineProcessing(el);
        el = await HtmlMailField.getInlineHTML(el, editableDocument);
        el.remove();
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
    extractProps({ attrs, options }, dynamicInfo) {
        const props = htmlField.extractProps({ attrs, options }, dynamicInfo);
        props.embeddedComponents = false;
        return props;
    },
};

registry.category("fields").add("html_mail", htmlMailField);
