import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class MobileSummaryKeyboard extends Interaction {
    static selector = ".o_mobile_summary";

    setup() {
        this.onFocusIn = this.onFocusIn.bind(this);
        this.onFocusOut = this.onFocusOut.bind(this);
    }

    start() {
        document.addEventListener("focusin", this.onFocusIn);
        document.addEventListener("focusout", this.onFocusOut);
    }

    destroy() {
        document.removeEventListener("focusin", this.onFocusIn);
        document.removeEventListener("focusout", this.onFocusOut);
    }

    onFocusIn(ev) {
        if (isMobileOS() && ev.target.matches("input, textarea, select")) {
            this.el.classList.remove("sticky-bottom");
        }
    }

    onFocusOut(ev) {
        if (ev.target.matches("input, textarea, select")) {
            this.el.classList.add("sticky-bottom");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_sale.mobile_summary_keyboard", MobileSummaryKeyboard);
