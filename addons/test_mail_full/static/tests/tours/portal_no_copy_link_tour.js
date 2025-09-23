import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

registry.category("web_tour.tours").add("portal_no_copy_link_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message",
            run: () => {
                const copyLinkAction = messageActionsRegistry.get("copy-link");
                patch(copyLinkAction, { sequence: 1 }); // make sure the action is visible without expanding
            }
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Test Message)",
            run: "hover && click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-actions",
            run: async () => {
                const copyLinkButton = document.querySelector('#chatterRoot').shadowRoot.querySelector("[title='Copy Link']");
                if (copyLinkButton) {
                    throw new Error("Users without read access should not be able to copy the link to a message");
                }
            },
        },
    ],
});
