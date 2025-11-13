import { after, ANIMATE, END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export class BlockquoteOption extends BaseOptionComponent {
    static template = "website.BlockquoteOption";
    static selector = ".s_blockquote";
    static components = { BorderConfigurator, ShadowOption };
}

export class WebsiteBackgroundBlockquoteOption extends BaseWebsiteBackgroundOption {
    static selector = ".s_blockquote";
    static defaultProps = {
        withColors: true,
        withImages: true,
        withShapes: true,
        withColorCombinations: true,
    };
}

class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    resources = {
        mark_color_level_selector_params: [{ selector: ".s_blockquote" }],
        builder_options: [
            withSequence(after(ANIMATE), WebsiteBackgroundBlockquoteOption),
            withSequence(END, BlockquoteOption),
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
