import { FONT_AWESOME } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { MassMailingFontAwesomeOption } from "@mass_mailing/builder/options/font_awesome_option";
import { registry } from "@web/core/registry";

class MassMailingFontAwesomeOptionPlugin extends Plugin {
    static id = "mass_mailing.FontAwesomeOption";
    resources = {
        builder_options: [withSequence(FONT_AWESOME, MassMailingFontAwesomeOption)],
    };
}

registry
    .category("builder-plugins")
    .add(MassMailingFontAwesomeOptionPlugin.id, MassMailingFontAwesomeOptionPlugin);
