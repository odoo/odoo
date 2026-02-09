import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
    },
    initState() {
        super.initState();
        this.uiState = {
            ...this.uiState,
            lineChanges: this.uiState.lineChanges || {},
            receiptReady: false,
        };
    },
    get unsentLines() {
        return this.lines.filter(
            (l) =>
                !Object.keys(this.uiState.lineChanges).includes(l.uuid) ||
                this.uiState.lineChanges[l.uuid].qty !== l.qty
        );
    },
    get changes() {
        return this.lines.reduce((acc, line) => {
            const diff = line.changes;
            if (
                diff.qty ||
                diff.customer_note ||
                diff.attribute_value_ids ||
                diff.custom_attribute_value_ids
            ) {
                acc[line.uuid] = diff;
            }
            return acc;
        }, {});
    },
    get isTakeaway() {
        return this.preset_id?.service_at !== "table" && this.config.use_presets;
    },
    recomputeChanges() {
        const lines = this.lines;
        for (const line of lines) {
            if (typeof line.id === "string") {
                continue;
            }

            this.uiState.lineChanges[line.uuid] = {
                qty: line.qty,
                customer_note: line.customer_note,
                attribute_value_ids: JSON.stringify(
                    line.attribute_value_ids.map((a) => a.id).sort()
                ),
                custom_attribute_value_ids: JSON.stringify(
                    line.custom_attribute_value_ids.map((a) => a.id).sort()
                ),
            };
        }

        for (const uuid of Object.keys(this.uiState.lineChanges)) {
            const line = this.lines.find((l) => l.uuid === uuid);
            if (!line) {
                delete this.uiState.lineChanges[uuid];
            }
        }
    },
    getLastOrderPreparationChange() {
        const preparation_change = {
            lines: {},
            general_customer_note: this.general_customer_note,
        };

        this.lines.forEach((line) => {
            preparation_change.lines[line.preparationKey] = {
                uuid: line.uuid,
                name: line.getFullProductName(),
                note: line.getNote(),
                customer_note: line.getCustomerNote(),
                product_id: line.getProduct().id,
                quantity: line.getQuantity(),
                attribute_value_ids: line.attribute_value_ids.map((attr) => attr.id),
            };
        });
        return preparation_change;
    },
});
