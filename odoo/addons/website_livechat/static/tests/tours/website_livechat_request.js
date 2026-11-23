/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { endDiscussion, okRating, feedback, transcript, close } from "./website_livechat_common";
import { registry } from "@web/core/registry";

odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName === "@im_livechat/embed/common/livechat_service") {
        const { LivechatService, ODOO_VERSION_KEY } = e.detail.module;
        // Livechat sessions are deleted if they come from a different odoo version than
        // the current one. Since each test is run with a different browser the version
        // is never set. This patch sets the version to the current one.
        patch(LivechatService.prototype, {
            async initialize() {
                try {
                    const response = await fetch("/web/webclient/version_info", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({}),
                    });
                    const { server_version: serverVersion } = (await response.json()).result;
                    localStorage.setItem(ODOO_VERSION_KEY, serverVersion);
                } catch {
                    // Could be intentional (tour ended successfully while version still loading)
                }

                return super.initialize(...arguments);
            },
        });
    }
});

const chatRequest = [
    {
        content: "Answer the chat request!",
        trigger: ".o-mail-Composer-input",
        run: "text Hi ! What a coincidence! I need your help indeed.",
    },
    {
        content: "Send the message",
        trigger: ".o-mail-Composer-input",
        run() {
            this.$anchor[0].dispatchEvent(
                new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
            );
        },
    },
    {
        content: "Verify your message has been typed",
        trigger: ".o-mail-Message:contains('Hi ! What a coincidence! I need your help indeed.')",
    },
    {
        content: "Verify there is no duplicates",
        trigger: ".o-mail-Thread",
        run() {
            if (
                this.$anchor.find(
                    ".o-mail-Message:contains('Hi ! What a coincidence! I need your help indeed.')"
                ).length === 1
            ) {
                $("body").addClass("no_duplicated_message");
            }
        },
    },
    {
        content: "Is your message correctly sent ?",
        shadow_dom: false,
        trigger: "body.no_duplicated_message",
        isCheck: true,
    },
];

registry.category("web_tour.tours").add("website_livechat_chat_request_part_1_no_close_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(chatRequest),
});

registry.category("web_tour.tours").add("website_livechat_chat_request_part_2_end_session_tour", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [].concat(endDiscussion, okRating, feedback, transcript, close),
});
