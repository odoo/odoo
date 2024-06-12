/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { sprintf } from "@web/core/utils/strings";
import { useSelectCreate, useOpenMany2XRecord} from "@web/views/fields/relational_utils";
export class SMLX2ManyField extends X2ManyField {
    setup() {
        super.setup();

        const selectCreate = useSelectCreate({
            resModel: "stock.quant",
            activeActions: this.activeActions,
            onSelected: (resIds) => this.selectRecord(resIds),
            onCreateEdit: () => this.createOpenRecord(),
        });

        this.selectCreate = (params) => {
            return selectCreate(params);
        };
        this.openQuantRecord = useOpenMany2XRecord({
            resModel: "stock.quant",
            activeActions: this.activeActions,
            onRecordSaved: (resId) => this.selectRecord([resId.data.id]),
            onRecordDiscarted: (resId) => this.selectRecord(resId),
            fieldString: this.props.string,
            is2Many: true,
        });
    }

    async onAdd({ context, editable } = {}) {
        context = {
            ...context,
            single_product: true,
            tree_view_ref: "stock.view_stock_quant_tree_simple",
        };
        const productName = this.props.record.data.product_id[1];
        const title = sprintf(this.env._t("Add line: %s"), productName);
        const alreadySelected = this.props.record.data.move_line_ids.records.filter((line) => line.data.quant_id?.[0]);
        const domain = [
            ["product_id", "=", this.props.record.data.product_id[0]],
            ["location_id", "child_of", this.props.context.default_location_id],
        ];
        if (alreadySelected.length) {
            domain.push(["id", "not in", alreadySelected.map((line) => line.data.quant_id[0])]);
        }
        return this.selectCreate({ domain, context, title });
    }

    selectRecord(res_ids) {
        const params = {
            context: { default_quant_id: res_ids[0] },
        };
        this.addInLine(params);
    }

    createOpenRecord() {
        const activeElement = document.activeElement;
        this.openQuantRecord({
            context: {
                ...this.props.context,
                form_view_ref: "stock.view_stock_quant_form",
            },
            immediate: true,
            onClose: () => {
                if (activeElement) {
                    activeElement.focus();
                }
            },
        });
    }
}

export const smlX2ManyField = {
    ...x2ManyField,
    component: SMLX2ManyField,
};

registry.category("fields").add("sml_x2_many", smlX2ManyField);
