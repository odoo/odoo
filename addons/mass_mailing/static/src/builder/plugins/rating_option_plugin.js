import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class MassMailingRatingOptionPlugin extends Plugin {
    static id = "mass_mailing.RatingOptionPlugin";
    resources = {
        // The base rating snippet of mailings has hollow inactive icons.
        hollow_rating_selectors: ".s_rating.o_mail_snippet_general",
    };
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingRatingOptionPlugin.id, MassMailingRatingOptionPlugin);
