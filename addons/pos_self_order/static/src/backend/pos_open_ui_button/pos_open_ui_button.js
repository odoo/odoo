import { PosOpenUIButton } from "@point_of_sale/backend/pos_open_ui_button/pos_open_ui_button";
import { useAsyncComputed } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(PosOpenUIButton.prototype, {
    setup() {
        super.setup();

        this.isKioskMode = useAsyncComputed(() => this.getConfig(this.props), { initial: false });
    },

    async getConfig({ record }) {
        const config_id = record.data?.config_id?.id;
        if (!config_id) {
            return;
        }
        const config_data = await this.orm.read("pos.config", [config_id], ["self_ordering_mode"]);
        return config_data[0]?.self_ordering_mode === "kiosk";
    },

    get isVisible() {
        return this.isKioskMode() ? false : super.isVisible;
    },
});
