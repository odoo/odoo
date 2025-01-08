import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { redirect } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";

export class ProfileValidation extends Interaction {
    static selector = ".o_wprofile_email_validation_container";
    dynamicContent = {
        ".send_validation_email": { "t-on-click.prevent.withTarget": this.onClickSend },
        ".validated_email_close": { "t-on-click": () => rpc("/profile/validate_email/close") },
    };

    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    async onClickSend(ev, currentTargetEl) {
        const data = await this.waitFor(rpc('/profile/send_validation_email', {
            redirect_url: currentTargetEl.dataset["redirect_url"],
        }));
        if (data) {
            redirect(currentTargetEl.dataset["redirect_url"]);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_profile.profile_validation", ProfileValidation);
