import { OpeningControlPopup } from "@point_of_sale/app/store/opening_control_popup/opening_control_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

patch(OpeningControlPopup.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
        this.confirm = useAsyncLockedMethod(this.confirm);
    },
    async confirm() {
        await super.confirm();
        if (this.pos.useBlackBoxBe() && !this.pos.checkIfUserClocked()) {
            await this.pos.clock(this.printer, true);
        }
        this.pos.user_session_status = await this.pos.getUserSessionStatus();
    },
});
