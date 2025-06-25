import { after, before, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

class ColumnOptionPlugin extends Plugin {
    static id = "columnPlugin";
    selector = ".col-lg";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            {
                OptionComponent: BorderConfigurator,
                selector: this.selector,
                props: {
                    label: "Border"
                }
            }
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("builder-plugins").add(ColumnOptionPlugin.id, ColumnOptionPlugin);
