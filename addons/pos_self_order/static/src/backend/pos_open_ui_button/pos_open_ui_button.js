import { asyncComputed, onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { PosOpenUIButton } from "@point_of_sale/backend/pos_open_ui_button/pos_open_ui_button";

patch(PosOpenUIButton.prototype, {
    setup() {
        super.setup(...arguments);

        this.isKioskMode = asyncComputed(() => this.getConfig(this.props), { initial: false });
        onWillStart(() => this.isKioskMode.currentPromise());
    },

    async getConfig(props) {
        const config_id = props.record.data?.config_id?.id;
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
