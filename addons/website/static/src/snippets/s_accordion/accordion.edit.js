import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Accordion extends Interaction {
    static selector = ".s_accordion";

    start() {
        // Introduced an interaction to fix a Firefox issue where buttons with
        // `contenteditable=true` ancestor were not editable. As a workaround,
        // we set buttons to `contenteditable=false` and made an inner `<span>`
        // editable to ensure accordion headers remain editable.
        const buttonEls = this.el.querySelectorAll(".accordion-button");
        buttonEls.forEach((buttonEl) => {
            buttonEl.setAttribute("contenteditable", "false");
            const spanEl = buttonEl.querySelector("span");
            if (spanEl) {
                spanEl.setAttribute("contenteditable", "true");
            }
        });
    }
}

registry
    .category("public.interactions.edit")
    .add("website.s_accordion", {
        Interaction: Accordion,
    });
