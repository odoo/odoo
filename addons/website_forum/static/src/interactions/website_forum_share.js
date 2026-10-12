import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class WebsiteForumShare extends Interaction {
    static selector = ".website_forum";

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
    }

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
                const bsModal = this.bootstrap.getOrCreateInstance(
                    window.Modal,
                    document.querySelector("#oe_social_share_modal")
                );
                bsModal.show();
            }

            sessionStorage.removeItem("social_share");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_forum.website_forum_share", WebsiteForumShare);
