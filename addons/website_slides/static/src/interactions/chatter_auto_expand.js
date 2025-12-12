import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { router } from "@web/core/browser/router";

export class ChatterAutoExpand extends Interaction {
    static selector = ".o_wslides_course_main";

    start() {
        if (router.current.highlight_message_id) {
            const reviewTab = this.el.querySelector("#review-tab");
            if (reviewTab) {
                const tabInstance = window.Tab.getOrCreateInstance(reviewTab);
                tabInstance?.show();
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.chatter_auto_expand", ChatterAutoExpand);
