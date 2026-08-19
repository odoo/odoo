import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

registry.category("web_tour.tours").add("portal_message_link_tour", {
    steps: () => [
        {
            trigger: ".o-mail-Message a.o_message_redirect",
            run() {
                // the tour cannot drive a new tab: follow the link in this one
                patch(window, {
                    open(url) {
                        return super.open(url, "_self");
                    },
                });
                this.anchor.click();
            },
            expectUnloadPage: true,
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message.o-highlighted:has(:text(Target message))",
        },
    ],
});
