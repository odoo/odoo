import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * This interaction tries to fix snippets that were malformed because of a missing
 * upgrade script. Without this, some newsletter snippets coming from users
 * upgraded from a version lower than 16.0 may not be able to update their
 * newsletter block.
 *
 * TODO an upgrade script should be made to fix databases and get rid of this.
 */

export class fixNewsletterListClass extends Interaction {
    static selector = ".s_newsletter_subscribe_form:not(.s_subscription_list), .s_newsletter_block";
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                s_newsletter_list: true,
            }),
        },
    };
}

registry
    .category("public.interactions.edit")
    .add("website_mass_mailing.fix_newsletter_list_class", {
        Interaction: fixNewsletterListClass,
    });
