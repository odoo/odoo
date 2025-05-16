import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

export class HttpError403 extends Interaction {
    static selector = ".s_403_error";

    start() {
        this.hideDebugBlock();
        this.appendDemoErrorCard();
    }

    hideDebugBlock() {
        const debugBlockEl = this.el.querySelector(".debug_block");
        if (debugBlockEl) {
            debugBlockEl.classList.add("d-none");
        }
    }

    appendDemoErrorCard() {
        const errorBlockEl = this.el.querySelector(".error_block");
        if (errorBlockEl && !this.el.querySelector(".card")) {
            const demoErrorCard = renderToElement(
                "website.http_error_403_demo_template"
            );
            errorBlockEl.replaceChild(demoErrorCard, errorBlockEl.firstElementChild);
        }
    }
}

registry.category("public.interactions.edit").add("website.http_error_403", {
    Interaction: HttpError403,
});
