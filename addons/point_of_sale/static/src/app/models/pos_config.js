import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { Base } from "./related_models";
import { getImageDataUrl } from "@point_of_sale/utils";
import { logPosMessage } from "../utils/pretty_console_log";
const CONSOLE_COLOR = "#F5B427";

export class PosConfig extends Base {
    static pythonModel = "pos.config";

    initState() {
        super.initState();
        this.uiState = {};
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

    get shouldLoadOrder() {
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
<<<<<<< 5eb60dce4b63ba36557ef94ba5f6a755dd20a7da

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
||||||| 77aedc0a396e17106e21b4062d492cfe13b8cdf1
=======

    get availablePricelists() {
        if (!this.use_pricelist) {
            return [];
        }
        const available_pricelists = new Set(this.available_pricelist_ids);
        available_pricelists.add(this.pricelist_id);
        return Array.from(available_pricelists);
    }
>>>>>>> 19bc34fb8e7c91762479cae0b8d2719329a0257b
}

registry.category("pos_available_models").add(PosConfig.pythonModel, PosConfig);
