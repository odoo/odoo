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
    static async getInlinedEditorContent(previousSibling, el) {
        if (!cssRulesByElement.has(previousSibling)) {
            cssRulesByElement.set(previousSibling, getCSSRules(previousSibling.ownerDocument));
        }
        const cssRules = cssRulesByElement.get(previousSibling);
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
        const previousSibling = this.editor.editable;
        return await HtmlMailField.getInlinedEditorContent(previousSibling, el);
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
