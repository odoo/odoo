import { patch } from "@web/core/utils/patch";
import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";

patch(OpeningControlPopup.prototype, {
    /**
     * @override
     */
    async confirm() {
        await super.confirm();
        await this.pos.updateStoreStatus(true);
    },
});
