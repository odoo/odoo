/** @odoo-module */
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { RPCError } from "@web/core/network/rpc_service";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { _t } from "@web/core/l10n/translation";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
    },
    async closeSession() {
        try {
            if (this.pos.useBlackBoxBe() && this.pos.checkIfUserClocked()) {
                await this.pos.clock(this.printer, false);
            }
            if (this.pos.useBlackBoxBe()) {
                try {
                    await this.orm.call("pos.session", "check_everyone_is_clocked_out", [
                        this.pos.pos_session.id,
                    ]);
                } catch (error) {
                    if (error instanceof RPCError) {
                        const { confirmed } = await this.popup.add(ConfirmPopup, {
                            title: _t("Multiple users clocked in"),
                            body: _t(
                                "Some users are still clocked in. You will be clocked out and redirected to the backend. Close the session from the other clocked in users."
                            ),
                        });
                        if (!confirmed) {
                            throw error;
                        }
                        await this.pos.closePos();
                        return;
                    }
                    throw error;
                }
            }
            this.pos.userSessionStatus = await this.pos.getUserSessionStatus();
            const result = await super.closeSession();
            if (result === false && this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
                await this.pos.clock(this.printer, true);
            }
            this.pos.userSessionStatus = await this.pos.getUserSessionStatus();
            return result;
        } catch (error) {
            if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
                await this.pos.clock(this.printer, true);
            }
            this.pos.userSessionStatus = await this.pos.getUserSessionStatus();
            throw error;
        }
    },
});
