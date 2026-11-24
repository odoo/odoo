import { OutOfFocusPlugin } from "@mail/core/common/out_of_focus_plugin";
import { patch } from "@web/core/utils/patch";

patch(OutOfFocusPlugin.prototype, {
    onWindowFocus() {
        super.onWindowFocus();
        this.store.updateAppBadge();
    },
});
