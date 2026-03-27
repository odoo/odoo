import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { before, VERTICAL_ALIGNMENT, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class MassMailingBorderOption extends BaseOptionComponent {
    static template = "mass_mailing.BorderOption";
    static components = { BorderConfigurator };
    withRoundCorner = true;
}

export class BorderOption1 extends MassMailingBorderOption {
    static selector =
        ".s_three_columns .row > div, .s_comparisons .row > div, .s_mail_block_event .row > div";
    static applyTo = ".card";
}

export class BorderOption2 extends MassMailingBorderOption {
    static selector = ".s_text_block, .o_mail_block_discount2";
}

export class BorderOption3 extends MassMailingBorderOption {
    static selector = "table, table td, table tr";
    withRoundCorner = false;
}

export class BorderOption4 extends MassMailingBorderOption {
    static selector = ".row > div";
    static exclude = [
        ".o_mail_wrapper_td, .s_image_gallery .row > div",
        BorderOption1.selector,
        BorderOption2.selector,
        BorderOption3.selector,
    ].join(",");
}

export class BorderOptionPlugin extends Plugin {
    static id = "mass_mailing.BorderOption";
    resources = {
        builder_options: [
            withSequence(before(WIDTH), BorderOption1),
            withSequence(before(WIDTH), BorderOption2),
            withSequence(before(WIDTH), BorderOption3),
            withSequence(VERTICAL_ALIGNMENT, BorderOption4),
        ],
    };
}

registry.category("mass_mailing-plugins").add(BorderOptionPlugin.id, BorderOptionPlugin);
