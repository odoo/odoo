import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { Base } from "./related_models";
import { getImageDataUrl } from "@point_of_sale/utils";

export class ResCompany extends Base {
    static pythonModel = "res.company";

    setup(vals) {
        super.setup(vals);
        this.uiState = {};
    }

    async cacheReceiptLogo() {
        try {
            this.uiState.receiptLogoDataUrl = await getImageDataUrl(this.receiptCompanyLogoUrl);
        } catch (error) {
            console.log("Error while caching receipt logo : ", error);
        }
    }

    get receiptLogoUrl() {
        return this.uiState.receiptLogoDataUrl || this.receiptCompanyLogoUrl;
    }

    get receiptCompanyLogoUrl() {
        return imageUrl("res.company", this.id, "logo", {
            width: 256,
            height: 256,
        });
    }
}
registry.category("pos_available_models").add(ResCompany.pythonModel, ResCompany);
