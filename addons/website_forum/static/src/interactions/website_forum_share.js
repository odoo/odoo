import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteForumShare extends Interaction {
    static selector = ".website_forum";

    start() {
        // Retrieve stored social data
        if (sessionStorage.getItem("social_share")) {
            const socialData = JSON.parse(sessionStorage.getItem("social_share"));

            if (socialData.targetType) {
                const questionEl = document.querySelector(".o_wforum_question");
                this.renderAt("website.social_modal", {
                    target_type: socialData.targetType,
                    state: questionEl.dataset.state,
                }, document.body, "beforeend", (els) => {
                    this.addListener(els[0], "hidden.bs.modal", () => els[0].remove());
                });
                const bsModal = window.Modal.getOrCreateInstance(document.querySelector("#oe_social_share_modal"));
                bsModal.show();
                this.registerCleanup(() => bsModal.dispose());
            }

            sessionStorage.removeItem("social_share");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_forum.website_forum_share", WebsiteForumShare);
