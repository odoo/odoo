import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";

export class GiftCardCopy extends Interaction {
    static selector = ".o_purchased_gift_card .copy-to-clipboard";
    dynamicContent = {
        _root: { "t-on-click": this.onClick },
    };

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        const textValue = ev.target.dataset.clipboardText;
        browser.navigator.clipboard.writeText(textValue);
    }
}

registry
    .category("public.interactions")
    .add("website_sale_loyalty.gift_card_copy", GiftCardCopy);
