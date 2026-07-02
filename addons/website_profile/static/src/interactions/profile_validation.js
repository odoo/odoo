import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { redirect } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";

export class ProfileValidation extends Interaction {
    static selector = ".o_wprofile_email_validation_container";
    dynamicContent = {
        ".send_validation_email": {
            "t-on-click.prevent": this.locked(this.onSendMailClick, true),
        },
        ".validated_email_close": { "t-on-click": () => rpc("/profile/validate_email/close") },
    };

    /**
     * @param {MouseEvent} ev
     */
    async onSendMailClick(ev) {
        const currentTarget = ev.currentTarget;
        const data = await this.waitFor(rpc('/profile/send_validation_email', {
            redirect_url: currentTarget.dataset["redirect_url"],
        }));
        if (data) {
            redirect(currentTarget.dataset["redirect_url"]);
            return new Promise(() => {});
        }
    }
}

registry
    .category("public.interactions")
    .add("website_profile.profile_validation", ProfileValidation);
