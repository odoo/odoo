import { MailPopoutPlugin } from "@mail/core/common/mail_popout_plugin";
import { Meeting } from "@mail/discuss/call/common/meeting";

import { Plugin, signal, usePlugin } from "@odoo/owl";

import { useEnv } from "@web/owl2/utils";

/** Shows the meeting of the call of `discuss.rtc` in a picture-in-picture window. */
export class PipPlugin extends Plugin {
    /** `discuss.rtc` is a legacy service, which starts after the plugins: read it lazily. */
    #env = useEnv();
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
     * @param {Component} [param0.context]
     */
    async open({ context } = {}) {
        const rtc = this.#env.services["discuss.rtc"];
        if (!rtc?.channel) {
            return;
        }
        this.isActive.set(true);
        const isShadowRoot = context?.root?.el?.getRootNode() instanceof ShadowRoot;
        const pipWindow = await this.#popout.pip(Meeting, {
            props: { isPip: true },
            options: { useAlternativeAssets: isShadowRoot },
        });
        pipWindow.addEventListener("keydown", (ev) => rtc.onKeyDown(ev));
        pipWindow.addEventListener("keyup", (ev) => rtc.onKeyUp(ev));
        pipWindow.document.body.style.backgroundColor = "black";
        pipWindow.document.body.style.overflow = "hidden";
        pipWindow.document.body.style.display = "block";
    }
}
