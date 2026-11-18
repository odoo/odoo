import { MailPopoutPlugin } from "@mail/core/common/mail_popout_plugin";
import { Meeting } from "@mail/discuss/call/common/meeting";

import { Plugin, signal, usePlugin } from "@odoo/owl";

/** Shows the meeting of the call of `discuss.rtc` in a picture-in-picture window. */
export class PipPlugin extends Plugin {
    #popout = usePlugin(MailPopoutPlugin).createManager("discuss.native.pip");
    isActive = signal(false);

    setup() {
        this.#popout.addHooks(undefined, () => this.isActive.set(false));
    }

    close() {
        this.#popout.reset();
        this.isActive.set(false);
        this.#popout.externalWindow?.close();
    }

    /**
     * @param {Object} [param0]
     * @param {Element} [param0.rootEl] an element of the page opening the picture-in-picture,
     *   to know whether it is in a shadow root (e.g. the livechat embed)
     * @returns {Promise<Window>} the picture-in-picture window
     */
    async open({ rootEl } = {}) {
        this.isActive.set(true);
        const isShadowRoot = rootEl?.getRootNode() instanceof ShadowRoot;
        const pipWindow = await this.#popout.pip(Meeting, {
            props: { isPip: true },
            options: { useAlternativeAssets: isShadowRoot },
        });
        pipWindow.document.body.style.backgroundColor = "black";
        pipWindow.document.body.style.overflow = "hidden";
        pipWindow.document.body.style.display = "block";
        return pipWindow;
    }
}
