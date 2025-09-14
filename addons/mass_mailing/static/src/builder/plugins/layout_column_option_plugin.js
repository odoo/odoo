import { LayoutColumnOption } from "@html_builder/plugins/layout_column_option";
import { before, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class MassMailingLayoutColumnPlugin extends Plugin {
    static id = "mass_mailing.LayoutColumnPlugin";
    resources = {
        mark_color_level_selector_params: [{ selector: ".o_mail_snippet_general" }],
        builder_options: [
            withSequence(before(WIDTH), {
                OptionComponent: LayoutColumnOption,
                selector: ".o_mail_snippet_general",
                exclude: ".s_reviews_wall",
                applyTo: ":scope > *:has(> .row:not(.s_nb_column_fixed)), * > .s_allow_columns",
            }),
        ],
    };
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingLayoutColumnPlugin.id, MassMailingLayoutColumnPlugin);
