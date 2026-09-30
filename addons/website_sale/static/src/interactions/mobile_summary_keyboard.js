import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class MobileSummaryKeyboard extends Interaction {
    static selector = ".o_mobile_summary";
    dynamicContent = {
        _document: {
            "t-on-focusin": this.onFocusIn,
            "t-on-focusout": this.onFocusOut,
        },
    };

    onFocusIn(ev) {
        if (isMobileOS() && ev.target.matches("input, textarea")) {
            this.el.classList.remove("sticky-bottom");
        }
    }

    onFocusOut(ev) {
        if (isMobileOS() && ev.target.matches("input, textarea")) {
            this.el.classList.add("sticky-bottom");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_sale.mobile_summary_keyboard", MobileSummaryKeyboard);
