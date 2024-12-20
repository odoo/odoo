import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";

class WebsiteForumShare extends Interaction {
    static selector = ".website_forum";

    start() {
        // Retrieve stored social data
        if (sessionStorage.getItem("social_share")) {
            const socialData = JSON.parse(sessionStorage.getItem("social_share"));

            if (socialData.targetType) {
                const questionEl = document.querySelector(".o_wforum_question");
                const modalEl = renderToElement("website.social_modal", {
                    target_type: socialData.targetType,
                    state: questionEl.dataset.state,
                });
                this.addListener(modalEl, "hidden.bs.modal", () => modalEl.remove());
                this.insert(modalEl, document.body);

                if (modalEl.querySelector(".s_share")) {
                    this.services["public.interactions"].startInteractions(modalEl.querySelector(".s_share"));
                }
                const bsModal = window.Modal.getOrCreateInstance(document.querySelector("#oe_social_share_modal"));
                bsModal.show();
                this.registerCleanup(() => bsModal.dispose());
            }

            sessionStorage.removeItem("social_share");
        }
    }
}

registry.category("public.interactions").add("website_forum.website_forum_share", WebsiteForumShare);
