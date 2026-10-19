import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { addLoadingEffect } from "@web/core/utils/ui";

export class WebsiteFormSubmit extends Interaction {
    static selector = ".js_website_submit_form";
    dynamicContent = {
        _root: { "t-on-submit": this.onSubmit },
    };

    onSubmit() {
        const submitEl = this.el.querySelector('button[type="submit"], a.a-submit');
        if (submitEl && !submitEl.disabled) {
            const removeLoadingEffect = addLoadingEffect(submitEl);
            this.registerCleanup(removeLoadingEffect);
        }
    }
}

registry.category("public.interactions").add("web.website_form_submit", WebsiteFormSubmit);
