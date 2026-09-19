/** @odoo-module native */
import { getImageDataUrl } from "@point_of_sale/utils";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";

import { logPosMessage } from "../utils/pretty_console_log.js";
import { Base } from "./related_models/index.js";
const CONSOLE_COLOR = "#F5B427";
const log = makeLogger("pos.config");

export class PosConfig extends Base {
    static pythonModel = "pos.config";

    initState() {
        super.initState();
        this.uiState = {};
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

    get orderedPaymentMethods() {
        return this.payment_method_ids.slice().sort((a, b) => a.sequence - b.sequence);
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
        const endCache = log.perf("cacheReceiptLogo");
        try {
            this.uiState.receiptLogoDataUrl = await getImageDataUrl(
                this.receiptCompanyLogoUrl,
            );
            endCache({ bytes: this.uiState.receiptLogoDataUrl?.length });
        } catch (error) {
            endCache({ failed: true });
            logPosMessage(
                "PosConfig",
                "cacheReceiptLogo",
                "Error while caching receipt logo",
                CONSOLE_COLOR,
                [error],
            );
        }
    }

    get receiptLogoUrl() {
        return this.uiState.receiptLogoDataUrl || this.receiptCompanyLogoUrl;
    }

    get receiptCompanyLogoUrl() {
        return imageUrl("res.company", this.company_id.id, "image_1920", {
            width: 256,
            height: 256,
        });
    }

    get availablePricelists() {
        if (!this.use_pricelist) {
            return [];
        }
        const available_pricelists = new Set(this.available_pricelist_ids);
        if (this.pricelist_id) {
            available_pricelists.add(this.pricelist_id);
        }
        log.logic("availablePricelists", () => ({
            config: this.id,
            count: available_pricelists.size,
            default: this.pricelist_id?.id,
        }));
        return Array.from(available_pricelists);
    }
}

registry.category("pos_available_models").add(PosConfig.pythonModel, PosConfig);
