import { Component, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { loadFields } from "@web/core/field_service";

export class Many2OneTaxTagsField extends Component {
    static template = "account.Many2OneTaxTagsField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.taxLabels = {};
        onWillStart(async () => {
            const taxModelFields = await loadFields("account.tax");
            for (const [taxKey, taxLabel] of taxModelFields.tax_scope.selection) {
                this.taxLabels[taxKey] = taxLabel;
            }
        });
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            searchMoreLabel: _t("Not sure... Help me!"),
            specification: {
                name: {},
                tax_scope: {},
            },
        };
    }
}

registry.category("fields").add("many2one_tax_tags", {
    ...buildM2OFieldDescription(Many2OneTaxTagsField),
    additionalClasses: ["o_field_many2one"],
});
