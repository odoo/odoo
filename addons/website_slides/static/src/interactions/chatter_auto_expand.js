import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class ChatterAutoExpand extends Interaction {
    static selector = ".o_wslides_course_main";

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
    }

    start() {
        if (router.current.highlight_message_id) {
            const reviewTab = this.el.querySelector("#review-tab");
            if (reviewTab) {
                this.bootstrap.getOrCreateInstance(window.Tab, reviewTab).show();
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.chatter_auto_expand", ChatterAutoExpand);
