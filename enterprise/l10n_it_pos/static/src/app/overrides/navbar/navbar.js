import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(Navbar.prototype, {
    async showRTStatus() {
        const result = await this.pos.fiscalPrinter.getRTStatus();
        if (result.success) {
            this.dialog.add(AlertDialog, {
                title: "RT Status",
                body: JSON.stringify(result.addInfo, null, 4),
            });
        }
    },
});
