import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BackgroundOptionPlugin extends Plugin {
    static id = "mass_mailing.BackgroundOption";
    resources = {
        builder_options: [
            {
                selector: ".s_masonry_block .row > div, .s_cover .oe_img_bg",
                OptionComponent: BackgroundOption,
                props: {
                    withImages: true,
                    withShapes: false,
                    withColors: true,
                    withColorCombinations: true,
                },
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);
