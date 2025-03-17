/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useSelectCreate, useOpenMany2XRecord} from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";

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
            search_default_on_hand: true,
            search_default_in_stock: true,
        };
        const productName = this.props.record.data.product_id[1];
        const title = _t("Add line: %s", productName);
        let domain = [
            ["product_id", "=", this.props.record.data.product_id[0]],
            ["location_id", "child_of", this.props.context.default_location_id],
        ];
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
        // Since changes of move line quantities will not affect the available quantity of the quant before
        // the record has been saved, it is necessary to determine the offset of the DB quant data.
        this.dirtyQuantsData.clear();
        const dirtyQuantityMoveLines = this.props.record.data.move_line_ids.records.filter(
            (ml) => !ml.data.quant_id && ml._values.quantity - ml._changes.quantity
        );
        const dirtyQuantMoveLines = this.props.record.data.move_line_ids.records.filter(
            (ml) => ml.data.quant_id[0]
        );
        const dirtyMoveLines = [...dirtyQuantityMoveLines, ...dirtyQuantMoveLines];
        if (!dirtyMoveLines.length) {
            return;
        }
        const match = await this.orm.call(
            "stock.move.line",
            "get_move_line_quant_match",
            [
                this.props.record.data.move_line_ids.records
                    .filter((rec) => rec.resId)
                    .map((rec) => rec.resId),
                this.props.record.resId,
                dirtyMoveLines.filter((rec) => rec.resId).map((rec) => rec.resId),
                dirtyQuantMoveLines.map((ml) => ml.data.quant_id[0]),
            ],
            {}
        );
        const quants = match[0];
        if (!quants.length) {
            return;
        }
        const dbMoveLinesData = new Map();
        for (const data of match[1]) {
            dbMoveLinesData.set(data[0], { quantity: data[1].quantity, quantId: data[1].quant_id });
        }
        const offsetByQuant = new Map();
        for (const ml of dirtyQuantMoveLines) {
            const quantId = ml.data.quant_id[0];
            offsetByQuant.set(quantId, (offsetByQuant.get(quantId) || 0) - ml.data.quantity);
            const dbQuantId = dbMoveLinesData.get(ml.resId)?.quantId;
            if (dbQuantId && quantId != dbQuantId) {
                offsetByQuant.set(
                    dbQuantId,
                    (offsetByQuant.get(dbQuantId) || 0) + dbMoveLinesData.get(ml.resId).quantity
                );
            }
        }
        const offsetByQuantity = new Map();
        for (const ml of dirtyQuantityMoveLines) {
            offsetByQuantity.set(ml.resId, ml._values.quantity - ml._changes.quantity);
        }
        for (const quant of quants) {
            const quantityOffest = quant[1].move_line_ids
                .map((ml) => offsetByQuantity.get(ml) || 0)
                .reduce((val, sum) => val + sum, 0);
            const quantOffest = offsetByQuant.get(quant[0]) || 0;
            this.dirtyQuantsData.set(quant[0], {
                available_quantity: quant[1].available_quantity + quantityOffest + quantOffest,
            });
        }
    }

    async selectRecord(res_ids) {
        const demand =
            this.props.record.data.product_uom_qty -
            this.props.record.data.move_line_ids.records
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
}

export const smlX2ManyField = {
    ...x2ManyField,
    component: SMLX2ManyField,
};

registry.category("fields").add("sml_x2_many", smlX2ManyField);
