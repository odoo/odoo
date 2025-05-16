import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

class HttpError403 extends Interaction {
    static selector = ".s_403_error";
    dynamicContent = {
        ".o_debug_block": {
            "t-att-class": () => ({
                "d-none": true,
            }),
        },
    };

    start() {
        this.appendDemoErrorCard();
    }

    appendDemoErrorCard() {
        this.errorBlockEl = this.el.querySelector(".o_error_block");
        if (this.errorBlockEl && !this.errorBlockEl.querySelector(".o_demo_card")) {
            this.originalContent = this.errorBlockEl.firstElementChild;
            this.demoErrorCard = renderToElement("website.http_error_403_demo_template");
            this.errorBlockEl.replaceChild(this.demoErrorCard, this.originalContent);
        }
    }

    destroy() {
        if (this.errorBlockEl) {
            this.errorBlockEl.replaceChild(this.originalContent, this.demoErrorCard);
        }
    }
}

registry.category("public.interactions.edit").add("website.http_error_403", {
    Interaction: HttpError403,
});
