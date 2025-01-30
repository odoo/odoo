import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class Many2OneUomField extends Component {
    static template = "uom.Many2OneUomField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            mapLoadedRecordToOption: ({ record }) => {
                const relativeInfo = record.relative_uom_id
                    ? `${record.relative_factor} ${record.relative_uom_id.display_name}`
                    : undefined;
                return {
                    value: record.id,
                    label: record.name ? record.name.split("\n")[0] : _t("Unnamed"),
                    relativeInfo,
                };
            },
            specification: {
                name: {},
                relative_factor: {},
                relative_uom_id: {
                    fields: {
                        display_name: {},
                    },
                },
            },
        };
    }
}

registry.category("fields").add("many2one_uom", {
    ...buildM2OFieldDescription(Many2OneUomField),
});
