import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BackgroundOptionPlugin extends Plugin {
    static id = "mass_mailing.BackgroundOption";
    resources = {
        builder_options: [
            {
                selector:
                    ".s_masonry_block > .container > .row > div:not(:has(.row)), .s_cover > .container > .row > div, .s_reviews_wall",
                OptionComponent: BackgroundOption,
                props: {
                    withImages: true,
                    withColors: false,
                    withColorCombinations: false,
                },
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
