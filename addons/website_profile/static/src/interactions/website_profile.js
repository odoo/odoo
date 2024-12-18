import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { redirect } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";

export class WebsiteProfile extends Interaction {
    static selector = ".o_wprofile_email_validation_container";
    dynamicContent = {
        ".send_validation_email": { "t-on-click.prevent": this.onClickSend },
        ".validated_email_close": { "t-on-click": () => rpc("/profile/validate_email/close") },
    };

    async onClickSend(ev) {
        const element = ev.currentTarget;
        const data = await this.waitFor(rpc('/profile/send_validation_email', {
            redirect_url: element.dataset["redirect_url"],
        }));
        if (data) {
            redirect(element.dataset["redirect_url"]);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_profile.website_profile", WebsiteProfile);
