import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { MassMailingImageAndFaOption } from "@mass_mailing/builder/options/image_and_fa_option";
import { ALIGNMENT_STYLE_PADDING } from "@html_builder/utils/option_sequence";

class MassMailingImageAndFaOptionPlugin extends Plugin {
    static id = "mass_mailing.ImageAndFaOption";
    resources = {
        builder_options: [withSequence(ALIGNMENT_STYLE_PADDING, MassMailingImageAndFaOption)],
    };
}

registry
    .category("builder-plugins")
    .add(MassMailingImageAndFaOptionPlugin.id, MassMailingImageAndFaOptionPlugin);
