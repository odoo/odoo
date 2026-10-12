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
        // Insert the cloned element inside an DOM so we can get its computed style.
        // Keep it out of the flow: it stays there while images load, and must
        // not resize its container (e.g. move the composer's Send button away
        // from the pointer between mousedown and mouseup). Only its content is
        // used, so these styles do not reach the email.
        Object.assign(el.style, {
            position: "fixed",
            top: "0",
            left: "0",
            width: `${editor.editable.getBoundingClientRect().width}px`,
            opacity: "0",
            pointerEvents: "none",
        });
        editor.editable.after(el);
        el.classList.remove("odoo-editor-editable");
        await toInline(el, cssRules);
        el.remove();
    }

    async getEditorContent() {
        const el = await super.getEditorContent();
        await HtmlMailField.getInlinedEditorContent(cssRulesByElement, this.editor, el);
        return el;
    }

    getConfig() {
        const config = super.getConfig();
        config.dropImageAsAttachment = false;
        config.defaultLinkAttributes = { target: "_blank", rel: "noreferrer noopener" };
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
