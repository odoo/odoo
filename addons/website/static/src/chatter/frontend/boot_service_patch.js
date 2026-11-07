import { patch } from "@web/core/utils/patch";
import { portalChatterBootService } from "@portal/chatter/boot/boot_service";

patch(portalChatterBootService, {
    canBoot() {
        // Do not boot the chatter in the website editor.
        return super.canBoot() && !document.body.classList.contains("editor_enable");
    },
});
