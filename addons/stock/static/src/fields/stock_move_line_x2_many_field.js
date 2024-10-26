/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useSelectCreate, useOpenMany2XRecord} from "@web/views/fields/relational_utils";
import { onMounted } from "@odoo/owl"
import { Domain } from "@web/core/domain";

export class SMLX2ManyField extends X2ManyField {
    setup() {
        super.setup();

        const selectCreate = useSelectCreate({
            resModel: "stock.quant",
            activeActions: this.activeActions,
            onSelected: (resIds) => this.selectRecord(resIds),
            onCreateEdit: () => this.createOpenRecord(),
        });

        onMounted(async () => {
            const orm = this.env.model.orm;
            this.quantsData = [];
            const usedByQuant = {};
            if (this.props.record.data.move_line_ids.records.length) {
                const domains = [];
                for (const ml of this.props.record.data.move_line_ids.records) {
                    domains.push([
                        ["product_id", "=", ml.data.product_id[0]],
                        ["lot_id", "=", ml.data.lot_id?.[0] || false],
                        ["location_id", "=", ml.data.location_id[0]],
                        ["package_id", "=", ml.data.package_id?.[0] || false],
                        ["owner_id", "=", ml.data.owner_id?.[0] || false],
                    ]);
                }
                if (domains.length) {
                    const quant_fields = ['display_name', 'product_id', 'lot_id', 'location_id', 'package_id', 'owner_id', 'available_quantity'];
                    const quants = await orm.searchRead("stock.quant", Domain.or(domains).toList(), quant_fields);
                    const quants_by_key = Object.fromEntries(quants.map(x => [
                        [x.product_id[0], x.lot_id?.[0] || false, x.location_id[0], x.package_id?.[0] || false, x.owner_id?.[0] || false],
                        [x.id, x.display_name, x.available_quantity]
                    ]));
                    for (const ml of this.props.record.data.move_line_ids.records) {
                        const entry = quants_by_key[[ml.data.product_id[0], ml.data.lot_id?.[0] || false, ml.data.location_id[0], ml.data.package_id?.[0] || false, ml.data.owner_id?.[0] || false].toString()];
                        if (!entry) {  // product not storable or has no quant yet
                            continue;
                        }
                        ml.data.quant_id = [entry[0], entry[1]];
                        usedByQuant[ml.data.quant_id[0]] = (usedByQuant[ml.data.quant_id[0]] || 0) + ml.data.quantity;
                    }
                    this.quantsData = quants.map(x => [x.id, x.available_quantity + (usedByQuant[x.id] || 0)]);
                }
            }
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
        context = {
            ...context,
            single_product: true,
            tree_view_ref: "stock.view_stock_quant_tree_simple",
            search_default_on_hand: true,
            search_default_in_stock: true,
        };
        const data = this.props.record.data;
        const productName = data.product_id[1];
        const title = _t("Add line: %s", productName);
        let domain = [
            ["product_id", "=", this.props.record.data.product_id[0]],
            ["location_id", "child_of", this.props.context.default_location_id],
        ];
        if (this.props.domain) {
            domain = [...domain, ...this.props.domain()];
        }
        const usedByQuant = this.props.record.data.move_line_ids.records.reduce((result, current) => {
            const quant_id = current.data.quant_id[0];
            if (!quant_id)
                return result;
            result[quant_id] = (result[quant_id] || 0) + current.data.quantity;
            return result;
        }, {});
        const fullyUsed = this.quantsData
            .filter(([id, available_quantity]) => (usedByQuant[id] || 0) >= available_quantity)
            .map(([id]) => id);

        if (fullyUsed.length)
            domain.push(["id", "not in", fullyUsed]);

        return this.selectCreate({ domain, context, title });
    }

    selectRecord(res_ids) {
        const params = {
            context: { default_quant_id: res_ids[0] },
        };
        this.list.addNewRecord(params).then(async (record) => {
            // Make it dirty to force the save of the record. addNewRecord make
            // the new record dirty === False by default to remove them at unfocus event
            record.dirty = true;
            if (record.data.quant_id[0] && this.quantsData.every(a => a[0] != record.data.quant_id[0])) {
                const orm = this.env.model.orm;
                const quants = await orm.searchRead("stock.quant", [["id", "=", record.data.quant_id[0]]], ['available_quantity']);
                this.quantsData.push([quants[0].id, quants[0].available_quantity]);
            }
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
