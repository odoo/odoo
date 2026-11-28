import { MailPopoutPlugin } from "@mail/core/common/mail_popout_plugin";

import { Plugin, signal, usePlugin } from "@odoo/owl";

import { registry } from "@web/core/registry";

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
     * @param {Component} [param0.context]
     * @returns {Promise<Window>} the picture-in-picture window
     */
    async open({ context } = {}) {
        this.isActive.set(true);
        const isShadowRoot = context?.root?.el?.getRootNode() instanceof ShadowRoot;
        const Meeting = registry.category("discuss.call/components").get("Meeting");
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
