import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { Base } from "./related_models";
import { getImageDataUrl } from "@point_of_sale/utils";
import { logPosMessage } from "../utils/pretty_console_log";
import { PosOrderlineAccounting } from "./accounting/pos_order_line_accounting";
import { PosOrderAccounting } from "./accounting/pos_order_accounting";

const CONSOLE_COLOR = "#F5B427";

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

    get useProxy() {
        return (
            this.is_posbox &&
            (this.iface_electronic_scale ||
                this.iface_print_via_proxy ||
                this.iface_scan_via_proxy ||
                this.iface_customer_facing_display_via_proxy)
        );
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

    async cacheReceiptLogo() {
        try {
            this.uiState.receiptLogoDataUrl = await getImageDataUrl(this.receiptCompanyLogoUrl);
        } catch (error) {
            logPosMessage(
                "PosConfig",
                "cacheReceiptLogo",
                "Error while caching receipt logo",
                CONSOLE_COLOR,
                [error]
            );
        }
    }

    get receiptLogoUrl() {
        return this.uiState.receiptLogoDataUrl || this.receiptCompanyLogoUrl;
    }

    get receiptCompanyLogoUrl() {
        return imageUrl("res.company", this.company_id.id, "logo", {
            width: 256,
            height: 256,
        });
    }
}

registry.category("pos_available_models").add(PosConfig.pythonModel, PosConfig);
