import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { Domain } from "@web/core/domain";

patch(PosStore.prototype, {
    getServerOrdersDomain() {
        const base = super.getServerOrdersDomain();
        if (this.session._self_ordering) {
            return Domain.or([
                base,
                new Domain([
                    ["company_id", "=", this.config.company_id.id],
                    ["state", "=", "draft"],
                    ["source", "=", "kiosk"],
                ]),
            ]);
        }
        return base;
    },
    async redirectToQrForm() {
        const user_data = await this.data.call("pos.config", "get_pos_qr_order_data", [
            this.config.id,
        ]);
        return await this.action.doAction({
            type: "ir.actions.client",
            tag: "pos_qr_stands",
            params: { data: user_data },
        });
    },
});
