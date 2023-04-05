/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { sprintf } from "@web/core/utils/strings";
import { useSelectCreate } from "@web/views/fields/relational_utils";
export class SMLX2ManyField extends X2ManyField {
    setup() {
        super.setup();
        const selectCreate = useSelectCreate({
            resModel: "stock.quant",
            activeActions: this.activeActions,
            onSelected: (resIds) => this.selectRecord(resIds),
            onCreateEdit: ({ context }) => this._openRecord({ context }),
        });

        this.selectCreate = (params) => {
            const p = Object.assign({}, params);
            return selectCreate(p);
        };
    }

    async onAdd({ context, editable } = {}) {
        context = {};
        const { string } = this.props;
        const title = sprintf(this.env._t("Add: %s"), string);
        const domain = [
            ["product_id", "=", this.props.record.data.product_id[0]],
            ["location_id", "child_of", this.props.context.default_location_id],
        ];
        return this.selectCreate({ domain, context, title });
    }

    selectRecord(res_ids) {
        const params = {
            context: { default_quant_id: res_ids[0] },
        };
        this.addInLine(params);
    }
}

export const smlX2ManyField = {
    ...x2ManyField,
    component: SMLX2ManyField,
};

registry.category("fields").add("sml_x2_many", smlX2ManyField);
