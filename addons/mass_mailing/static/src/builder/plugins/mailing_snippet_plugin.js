import { LayoutColumnOption } from "@html_builder/plugins/layout_column_option";
import { after, before, LAYOUT_COLUMN, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class MailingSnippetPlugin extends Plugin {
    static id = "MailingSnippetPlugin";
    resources = {
        mark_color_level_selector_params: [{ selector: ".o_mail_snippet_general" }],
        builder_options: [
            withSequence(before(WIDTH), {
                OptionComponent: LayoutColumnOption,
                selector: ".o_mail_snippet_general",
                applyTo: ":scope > *:has(> .row:not(.s_nb_column_fixed)), * > .s_allow_columns",
            }),
            withSequence(after(LAYOUT_COLUMN), {
                template: "mass_mailing.HeightOption",
                selector: ".o_mail_snippet_general",
                exclude: ".o_mail_snippet_general .row > div *",
            }),
        ],
    };
}

registry.category("mass_mailing-plugins").add(MailingSnippetPlugin.id, MailingSnippetPlugin);
