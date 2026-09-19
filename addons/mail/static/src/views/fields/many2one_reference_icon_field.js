import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { extractM2OFieldProps } from "@web/views/fields/many2one/many2one_field";
import { Many2OneReferenceField } from "@web/views/fields/many2one_reference/many2one_reference_field";

/**
 * The document an activity was logged on, shown with the icon of its model. A module
 * registers the icon of each model it owns:
 * `registry.category("mail.log_document_icons").add("crm.lead", { icon: "star", filled: true })`
 */
export class Many2OneReferenceIconField extends Many2OneReferenceField {
    static template = "mail.Many2OneReferenceIconField";

    get iconDefinition() {
        return registry.category("mail.log_document_icons").get(this.relation, {});
    }

    get modelIcon() {
        return this.iconDefinition.icon || "description";
    }

    get modelIconClass() {
        return this.iconDefinition.filled ? "oi-filled" : "";
    }

    /** Name of the document's model, when the record carries it: a module whose records
     * hold that name overrides this to have it shown as a tooltip. */
    get modelDisplayName() {
        return "";
    }
}

registry.category("mail.log_document_icons").add("res.partner", { icon: "contact_page" });
registry.category("mail.log_document_icons").add("res.users", { icon: "person" });

registry.category("fields").add("many2one_reference_icon", {
    component: Many2OneReferenceIconField,
    displayName: _t("Many2OneReference with Icon"),
    extractProps(staticInfo, dynamicInfo) {
        return extractM2OFieldProps(staticInfo, dynamicInfo);
    },
    relatedFields: [{ name: "display_name", type: "char" }],
    supportedTypes: ["many2one_reference"],
});
