import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";
import { patch } from "@web/core/utils/patch";

patch(OutOfFocusService.prototype, {
    onWindowFocus() {
        super.onWindowFocus();
        this.store.updateAppBadge();
    },
});
