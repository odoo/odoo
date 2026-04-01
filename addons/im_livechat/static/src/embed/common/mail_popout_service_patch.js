import { patch } from "@web/core/utils/patch";
import { loadAssets } from "@im_livechat/embed/common/boot_helpers";
import { mailPopoutService } from "@mail/core/common/mail_popout_service";

const popoutPatch = {
    async addAssets(window) {
        await super.addAssets(...arguments);
        // Wait for the new window to be fully loaded and ready
        await new Promise((resolve) => {
            if (window.document.readyState === "complete") {
                resolve();
            } else {
                window.addEventListener("load", resolve, { once: true });
            }
        });
        // FIXME: without this, fonts detected on the document are incorrect,
        // they seem to default to the font list of the parent window,
        // even though this same promise is awaited before checking the fonts in `loadFont`
        await window.document.fonts.ready;
        await loadAssets(window.document.head);
    },
};
patch(mailPopoutService, popoutPatch);
