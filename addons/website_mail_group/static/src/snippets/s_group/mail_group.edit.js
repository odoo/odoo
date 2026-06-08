import { MailGroup } from "@mail_group/interactions/mail_group";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// TODO should probably have a better way to handle this, maybe the invisible
// block system could be extended to handle this kind of things. Here we only
// do the same as the non-edit mode public widget: showing and hiding the widget
// but without the rest. Arguably could just enable the whole widget in edit
// mode but not stable-friendly.
export class MailGroupEdit extends Interaction {
    static selector = MailGroup.selector;
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                "d-none": false,
            }),
        },
    };
}

registry
    .category("public.interactions.edit")
    .add("website_mail_group.mail_group", {
        Interaction: MailGroupEdit,
    });
