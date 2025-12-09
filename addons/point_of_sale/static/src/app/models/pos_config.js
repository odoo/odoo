import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { PosOrderlineAccounting } from "./accounting/pos_order_line_accounting";
import { PosOrderAccounting } from "./accounting/pos_order_accounting";

export class PosConfig extends Base {
    static pythonModel = "pos.config";

    initState() {
        super.initState();
        this.uiState = {};
        this.handlePricesComputation();
    }

    /**
     * Since order lines prices needs to be computed globally we need to recompute the whole
     * order prices each time an order line is created or updated.
     */
    handlePricesComputation() {
        const lineModel = this.models["pos.order.line"];
        const orderModel = this.models["pos.order"];

        const updateLinePrices = (ids, fields) => {
            const fieldTargetted = fields?.some((field) =>
                PosOrderlineAccounting.accountingFields.has(field)
            );

            if (fieldTargetted || !fields) {
                // Orders needs to be read from raw in case of not fully setuped records
                const lines = lineModel.readMany(ids);
                const orderIds = new Set(lines.map((l) => l.raw.order_id));
                const orders = orderModel.readMany([...orderIds]);
                orders.forEach((order) => order.triggerRecomputeAllPrices());
            }
        };

        const updateOrderPrices = (id, fields) => {
            const fieldTargetted = fields?.some((field) =>
                PosOrderAccounting.accountingFields.has(field)
            );

            if (fieldTargetted) {
                const order = orderModel.get(id);
                order?.triggerRecomputeAllPrices();
            }
        };

        lineModel.addEventListener("create", (data) => updateLinePrices(data.ids));
        lineModel.addEventListener("update", (data) => updateLinePrices([data.id], data.fields));
        orderModel.addEventListener("update", (data) => updateOrderPrices(data.id, data.fields));
    }

    get hasCashRounding() {
        return this.cash_rounding && this.only_round_cash_method;
    }
    get hasGlobalRounding() {
        return this.cash_rounding && !this.only_round_cash_method;
    }
    get canInvoice() {
        return Boolean(this.raw.invoice_journal_id);
    }

    get isShareable() {
        return this.raw.trusted_config_ids.length > 0;
    }

    get printerCategories() {
        const set = new Set();
        for (const relPrinter of this.models["pos.printer"].getAll()) {
            const printer = relPrinter.raw;
            for (const id of printer.product_categories_ids) {
                set.add(id);
            }
        }
        return set;
    }

    get preparationCategories() {
        if (this.printerCategories) {
            return new Set([...this.printerCategories]);
        }
        return new Set();
    }

    get displayBigTrackingNumber() {
        return false;
    }

    get displayTrackingNumber() {
        return this.module_pos_restaurant;
    }

    get receiptLogoUrl() {
        return this.logo ? `data:image/png;base64,${this.logo}` : false;
    }
}

registry.category("pos_available_models").add(PosConfig.pythonModel, PosConfig);
