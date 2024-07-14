/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";

export class SignerX2Many extends X2ManyField {
    static template = "sign.SignerX2Many";
    static components = {
        ...X2ManyField.components,
        Many2OneField,
        IntegerField,
    };

    static props = {
        ...X2ManyField.props,
        context: { type: Object, optional: true },
    };

    get partnerIdFieldInfo() {
        return {
            name: "partner_id",
            additionalProps: {
                readonly: false,
                placeholder: _t("Type a name or email..."),
                context: "{'force_email': True, 'show_email': True}",
            },
        };
    }

    get shouldShowOrder() {
        return this.props.record.data["set_sign_order"];
    }
}

const signerX2Many = {
    component: SignerX2Many,
    displayName: _t("Signer One 2 Many"),
    additionalClasses: ["o_required_modifier"],
    supportedTypes: ["one2many"],
    relatedFields: () => {
        return [
            { name: "role_id", type: "many2one", relation: "sign.item.role", readonly: false },
            { name: "partner_id", type: "many2one", relation: "res.partner", readonly: false },
            { name: "mail_sent_order", type: "integer", readonly: false },
        ];
    },
    fieldDependencies: [{ name: "set_sign_order", type: "boolean" }],
};

registry.category("fields").add("signer_x2many", signerX2Many);
