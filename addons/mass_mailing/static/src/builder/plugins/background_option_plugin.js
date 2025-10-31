import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MailingBackgroundOption extends BackgroundOption {
    static selector =
        ".s_masonry_block > .container > .row > div:not(:has(.row)), .s_cover > .container > .row > div, .s_reviews_wall";
    static props = {
        ...BackgroundOption.props,
        withColors: { type: Boolean, optional: true },
        withImages: { type: Boolean, optional: true },
        withColorCombinations: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withImages: true,
        withColors: false,
        withColorCombinations: false,
    };
}

class BackgroundOptionPlugin extends Plugin {
    static id = "mass_mailing.BackgroundOption";
    resources = {
        builder_options: MailingBackgroundOption,
    };
}

registry.category("mass_mailing-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
