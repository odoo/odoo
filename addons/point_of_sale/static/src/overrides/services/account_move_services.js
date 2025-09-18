import { AccountMoveService } from "@account/services/account_move_service";
import { isIOS, isIosApp } from "@web/core/browser/feature_detection";
import { patch } from "@web/core/utils/patch";
patch(AccountMoveService.prototype, {
    async downloadPdf(accountMoveId, target = "download") {
        if (isIosApp() || isIOS()) {
            return super.downloadPdf(accountMoveId, "_blank");
        }
        super.downloadPdf(accountMoveId, target);
    },
});
