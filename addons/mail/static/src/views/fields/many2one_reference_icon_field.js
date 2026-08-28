import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { extractM2OFieldProps } from "@web/views/fields/many2one/many2one_field";
import { Many2OneReferenceField } from "@web/views/fields/many2one_reference/many2one_reference_field";

export const ICON_BY_MODEL_NAME = {
    "crm.lead": "star",
    "sale.order": "attach_money",
    "account.move": "file_export",
    subscription: "refresh",
    "event.event": "calendar_today",
    "helpdesk.ticket": "support",
    "project.task": "check",
    "purchase.order": "credit_card",
    "document.document": "article",
    "hr.employee": "badge",
    "stock.picking": "local_shipping",
    "res.partner": "contact_page",
    "mrp.production": "build",
    "hr.applicant": "account_circle",
    "fleet.vehicle": "directions_car",
};

export class Many2OneReferenceIconField extends Many2OneReferenceField {
    static template = "mail.Many2OneReferenceIconField";

    /** Icon of the related model, "description" for a model with no specific icon. */
    get modelIcon() {
        // flag set by voip_sale_subscription, to tell a subscription from a plain sale order
        if (this.props.record.data.is_related_activity_document_subscription) {
            return ICON_BY_MODEL_NAME["subscription"];
        }
        return ICON_BY_MODEL_NAME[this.relation] || "description";
    }

    get modelIconClass() {
        return this.relation === "crm.lead" || this.relation === "event.event" ? "oi-filled" : "";
    }
}

registry.category("fields").add("many2one_reference_icon", {
    component: Many2OneReferenceIconField,
    displayName: _t("Many2OneReference with Icon"),
    extractProps(staticInfo, dynamicInfo) {
        return extractM2OFieldProps(staticInfo, dynamicInfo);
    },
    relatedFields: [{ name: "display_name", type: "char" }],
    supportedTypes: ["many2one_reference"],
});
