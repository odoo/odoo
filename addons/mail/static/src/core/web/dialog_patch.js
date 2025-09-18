import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/ui/dialog/dialog";
patch(Dialog.prototype, {
    /**
     * @override
     */
    onEscape() {
        if (this.data.model === "mail.compose.message") {
            return;
        }
        super.onEscape();
    },
});
