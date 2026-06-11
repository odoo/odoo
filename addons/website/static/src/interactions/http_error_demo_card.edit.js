import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class HttpErrorDemoCard extends Interaction {
    static selector = "#o_error_block";

    start() {
        /**
         * Replaces the original error block content with a demo error card.
         * The demo card is restored to the original content when the
         * interaction is destroyed.
         */
        this.removeChildren(this.el);
        this.renderAt("website.http_error_demo_card_template", {}, this.el);
    }
}

registry.category("public.interactions.edit").add("website.http_error_demo_card", {
    Interaction: HttpErrorDemoCard,
});
