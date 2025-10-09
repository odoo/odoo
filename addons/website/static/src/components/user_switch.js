import { UserSwitch } from "@web/core/user_switch/user_switch";
import { patch } from "@web/core/utils/patch";

patch(UserSwitch.prototype, {
    toggleFormDisplay() {
        if (document.body.classList.contains("editor_enable")) {
            return;
        }
        super.toggleFormDisplay();
    },
});
