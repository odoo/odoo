import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useSelectCreate, useOpenMany2XRecord} from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { computeDirtyQuantsData } from "@stock/helpers/dirty_quants";

export class SMLX2ManyField extends X2ManyField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dirtyQuantsData = new Map();
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
            fieldString: this.props.string,
            is2Many: true,
        });
    }

    get quantListViewShowOnHandOnly(){
        return true; // To override in mrp_subcontracting
    }

    async onAdd({ context, editable } = {}) {
        if (!this.props.record.data.show_quant) {
            return super.onAdd(...arguments);
        }
        // Compute the quant offset from move lines quantity changes that were not saved yet.
        // Hence, did not yet affect quant's quantity in DB.
        await this.updateDirtyQuantsData();
        context = {
            ...context,
            single_product: true,
            list_view_ref: "stock.view_stock_quant_tree_simple",
        };
        const productName = this.props.record.data.product_id.display_name;
        const title = _t("Add line: %s", productName);
        let domain = [
            ["product_id", "=", this.props.record.data.product_id.id],
            ["location_id", "child_of", this.props.context.default_location_id],
            ["quantity", ">", 0.0],
        ];
        if (this.quantListViewShowOnHandOnly) {
            domain.push(["on_hand", "=", true]);
        }
        if (this.dirtyQuantsData.size) {
            const notFullyUsed = [];
            const fullyUsed = [];
            for (const [quantId, quantData] of this.dirtyQuantsData.entries()) {
                if (quantData.available_quantity > 0) {
                    notFullyUsed.push(quantId);
                } else {
                    fullyUsed.push(quantId);
                }
            }
            if (fullyUsed.length) {
                domain = Domain.and([domain, [["id", "not in", fullyUsed]]]).toList();
            }
            if (notFullyUsed.length) {
                domain = Domain.or([domain, [["id", "in", notFullyUsed]]]).toList();
            }
        }
        return this.selectCreate({ domain, context, title });
    }

    async updateDirtyQuantsData() {
        this.dirtyQuantsData = await computeDirtyQuantsData(
            this.orm,
            this.props.record.resId,
            this.list,
            this._move_line_ids
        );
    }

    async selectRecord(res_ids) {
        const demand =
            this.props.record.data.product_uom_qty -
            this._move_line_ids
                .map((ml) => ml.data.quantity)
                .reduce((val, sum) => val + sum, 0);
        const params = {
            context: { default_quant_id: res_ids[0] },
        };
        if (demand <= 0) {
            params.context.default_quantity = 0;
        } else if (this.dirtyQuantsData.has(res_ids[0])) {
            params.context.default_quantity = Math.min(
                this.dirtyQuantsData.get(res_ids[0]).available_quantity,
                demand
            );
        }
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

    get _move_line_ids() {
        return this.props.record.data.move_line_ids.records;
    }
}

export const smlX2ManyField = {
    ...x2ManyField,
    component: SMLX2ManyField,
};

registry.category("fields").add("sml_x2_many", smlX2ManyField);
