import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";


export class CopyButton extends Interaction {
    static selector = '.copy-button';
    dynamicContent = {
        _root: { 't-on-click': this.onClick },
    };

    setup() {
        this.copyText = this.el; // get attr copyText
        this.displayText = '' ; // before clicking
        this.successText = ''; // after clikcing
    }

    onClick() {
        browser.navigator.clipboard.writeText(this.copyText);
    }
}

registry
    .category("public.interactions")
    .add("website_sale.copy_button", CopyButton);
