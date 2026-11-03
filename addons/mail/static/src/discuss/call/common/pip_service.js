import { Meeting } from "./meeting";
import { MailPopoutPlugin } from "@mail/core/common/mail_popout_plugin";

import { proxy, usePlugin } from "@odoo/owl";

import { registry } from "@web/core/registry";

export const callPipService = {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    start(env) {
        const popout = usePlugin(MailPopoutPlugin).createManager("discuss.native.pip");
        let pipWindow = null;
        const state = proxy({ active: false });
        popout.addHooks(
            () => {},
            () => {
                state.active = false;
                env.services["discuss.rtc"]?.channel?.openChatWindow();
            }
        );
        function closePip() {
            popout.reset();
            state.active = false;
            pipWindow?.close();
        }
        /**
         * @param {Object} [param0] native pip options
         * @param {Component} [param0.context]
         */
        async function openPip({ context }) {
            const rtc = env.services["discuss.rtc"];
            if (!rtc?.channel) {
                return;
            }
            state.active = true;
            const isShadowRoot = context?.root?.el?.getRootNode() instanceof ShadowRoot;
            pipWindow = await popout.pip(Meeting, {
                props: { isPip: true },
                options: { useAlternativeAssets: isShadowRoot },
            });
            pipWindow.addEventListener("keydown", (ev) => {
                rtc.onKeyDown(ev);
            });
            pipWindow.addEventListener("keyup", (ev) => {
                rtc.onKeyUp(ev);
            });
            pipWindow.document.body.style.backgroundColor = "black";
            pipWindow.document.body.style.overflow = "hidden";
            pipWindow.document.body.style.display = "block";
        }
        return proxy({
            get isNativePipAvailable() {
                return Boolean(window.documentPictureInPicture);
            },
            get pipWindow() {
                return pipWindow;
            },
            state,
            closePip,
            openPip,
        });
    },
};

registry.category("services").add("discuss.pip_service", callPipService);
