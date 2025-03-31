import { AccountMoveService } from "@account/services/account_move_service";
import { isIosApp, isIOS } from "@web/core/browser/feature_detection";
import { patch } from "@web/core/utils/patch";

patch(AccountMoveService.prototype, {
    async downloadPdf(accountMoveId) {
        if (isIosApp() || isIOS()) {
            return await this.action.doAction({
                type: "ir.actions.act_url",
                url: `/account/download_invoice_documents/${accountMoveId}/pdf`,
            });
        }
        return super.downloadPdf(accountMoveId);
    },
});
