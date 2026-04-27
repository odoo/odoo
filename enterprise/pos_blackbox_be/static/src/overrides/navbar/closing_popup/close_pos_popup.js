import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";

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
                    await this.pos.data.call("pos.session", "check_everyone_is_clocked_out", [
                        this.pos.session.id,
                    ]);
                } catch (error) {
                    if (error instanceof RPCError) {
                        const { confirmed } = await ask(this.dialog, {
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
            this.pos.user_session_status = await this.pos.getUserSessionStatus();
            const result = await super.closeSession();
            if (result === false && this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
                await this.pos.clock(this.printer, true);
            }
            this.pos.user_session_status = await this.pos.getUserSessionStatus();
            return result;
        } catch (error) {
            if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
                await this.pos.clock(this.printer, true);
            }
            this.pos.user_session_status = await this.pos.getUserSessionStatus();
            throw error;
        }
    },
});
