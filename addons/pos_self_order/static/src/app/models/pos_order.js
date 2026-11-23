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
<<<<<<< 19c123142bc56a5d82f4d21658253fe71da8d48b
||||||| 0a6b16e7d80802c8eb252960ef77cd1dd7f2f4b1
            receiptReady: false,
=======
            lastGeneralCustomerNote: this.uiState.lastGeneralCustomerNote || "",
            receiptReady: false,
>>>>>>> 9337b2c388a1a278aa069f71f0106819c4ccc5c8
        };
    },
    get unsentLines() {
        return this.lines.filter(
            (l) =>
                !l.isTipLine() &&
                (!Object.keys(this.uiState.lineChanges).includes(l.uuid) ||
                    this.uiState.lineChanges[l.uuid].qty !== l.qty)
        );
    },
    get changes() {
        return this.lines.reduce((acc, line) => {
            // Tip isn't tracked as a change. counting it would mark an unsent change and could block payment.
            if (line.isTipLine()) {
                return acc;
            }
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
    get hasGeneralNoteChange() {
        return this.general_customer_note !== this.uiState.lastGeneralCustomerNote;
    },
    get isTakeaway() {
        return this.preset_id?.service_at !== "table" && this.config.use_presets;
    },
    recomputeChanges() {
        const lines = this.lines;
        this.uiState.lastGeneralCustomerNote = this.general_customer_note;
        for (const line of lines) {
            if (!line.isSynced) {
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
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this.mobile && !data.mobile) {
            data.mobile = this.mobile;
        }
        if (this.email && !data.email) {
            data.email = this.email;
        }
        data.partner_id = this.raw.partner_id || false;
        return data;
    },
});
