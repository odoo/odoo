import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

patch(Dialog.prototype, {
    /**
     * @override
     */
    onEscape() {
        const messageModels = ["mail.compose.message", "mail.scheduled.message"];
        if (messageModels.includes(this.data.model)) {
            return;
        }
        super.onEscape();
    },
});
