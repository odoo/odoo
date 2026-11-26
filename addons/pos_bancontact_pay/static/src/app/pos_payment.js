import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

patch(PosPayment.prototype, {
    getQrPopupProps() {
        const base = super.getQrPopupProps();
        const lang = this.pos_order_id?.user_id?.lang?.split("_")?.[0];
        const supportedLanguages = ["fr", "nl"];
        const frameLanguage = lang && supportedLanguages.includes(lang) ? lang : "fr";
        return { ...base, frameLanguage };
    },
});
