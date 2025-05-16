import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class HttpError403 extends Interaction {
    static selector = ".s_403_error";

    start() {
        this.appendDemoErrorCard();
    }

    /**
     * Replaces the original error block content with a demo error card.
     * The demo card is restored to the original content when the interaction
     * is destroyed.
     */
    appendDemoErrorCard() {
        this.demoCardEL = this.el.querySelector(".o_demo_card");
        if (this.demoCardEL != null) {
            this.renderAt("website.http_error_403_demo_template", {}, this.el);
        }
    }
}

registry.category("public.interactions.edit").add("website.http_error_403", {
    Interaction: HttpError403,
});
