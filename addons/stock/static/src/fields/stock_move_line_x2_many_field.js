/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
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
            onRecordSaved: (record) => this.selectRecord([record.resId]),
            onRecordDiscarted: (resId) => this.selectRecord(resId),
            fieldString: this.props.string,
            is2Many: true,
        });
    }

    async onAdd({ context, editable } = {}) {
        if (!this.props.record.data.show_quant) {
            return super.onAdd(...arguments);
        }
        context = {
            ...context,
            single_product: true,
            tree_view_ref: "stock.view_stock_quant_tree_simple",
            search_default_on_hand: true,
            search_default_in_stock: true,
        };
        const productName = this.props.record.data.product_id[1];
        const title = _t("Add line: %s", productName);
        const alreadySelected = this.props.record.data.move_line_ids.records.filter((line) => line.data.quant_id?.[0]);
        let domain = [
            ["product_id", "=", this.props.record.data.product_id[0]],
            ["location_id", "child_of", this.props.context.default_location_id],
        ];
        if (this.props.domain) {
            domain = [...domain, ...this.props.domain()];
        }
        if (alreadySelected.length) {
            domain.push(["id", "not in", alreadySelected.map((line) => line.data.quant_id[0])]);
        }
        return this.selectCreate({ domain, context, title });
    }

    selectRecord(res_ids) {
        const params = {
            context: { default_quant_id: res_ids[0] },
        };
        this.list.addNewRecord(params).then((record) => {
            // Make it dirty to force the save of the record. addNewRecord make
            // the new record dirty === False by default to remove them at unfocus event
            record.dirty = true;
        });
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
