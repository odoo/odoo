import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { getCSSRules, toInline } from "./convert_inline";
import { ColumnPlugin } from "@html_editor/main/column_plugin";
import { user } from "@web/core/user";

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
        config.Plugins = config.Plugins.filter((plugin) => plugin !== ColumnPlugin);
        config.dynamicFieldFilter = this.dynamicFieldFilter.bind(this);
        config.dynamicFieldPreprocess = ({ resModel }) => this.loadAllowedExpressions(resModel);
        config.dynamicFieldPostprocess = this.dynamicFieldPostprocess.bind(this);
        return config;
    }

    dynamicFieldFilter(fieldDef, path) {
        const fullPath = `object${path ? `.${path}` : ""}.${fieldDef.name}`;
        if (!this.isTemplateEditor && !this.allowedQwebExpressions.includes(fullPath)) {
            return false;
        }
        return !["one2many", "boolean", "many2many"].includes(fieldDef.type) && fieldDef.searchable;
    }

    async dynamicFieldPostprocess({ path, label, fieldInfo, resModel, element }) {
        if (fieldInfo.type !== "datetime") {
            return;
        }

        const partnerFields = await this.ormService.call(resModel, "mail_get_partner_fields", [[]]);

        let out = partnerFields.length
            ? `format_datetime(${path}, tz=object.${partnerFields[0]}.tz)`
            : `format_datetime(${path})`;

        if (label) {
            const safeDefaultValue = label.replace(/'/g, "\\'");
            out += ` or '${safeDefaultValue}'`;
        }

        element.setAttribute("t-out", out);
        element.removeAttribute("t-field");
    }

    async loadAllowedExpressions(resModel) {
        const getAllowedQwebExpressions = this.env.services["allowed_qweb_expressions"];
        [this.isTemplateEditor, this.allowedQwebExpressions] = await Promise.all([
            user.hasGroup("mail.group_mail_template_editor"),
            getAllowedQwebExpressions(resModel),
        ]);
    }
}

export const htmlMailField = {
    ...htmlField,
    component: HtmlMailField,
    additionalClasses: ["o_field_html"],
    extractProps({ attrs, options }, dynamicInfo) {
        const props = htmlField.extractProps({ attrs, options }, dynamicInfo);
        props.editorConfig.allowChecklist = false;
        props.embeddedComponents = false;
        return props;
    },
};

registry.category("fields").add("html_mail", htmlMailField);
