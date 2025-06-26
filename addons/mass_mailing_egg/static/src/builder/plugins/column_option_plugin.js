import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { _t } from "@web/core/l10n/translation";

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
                    label: _t("Border")
                }
            }
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("builder-plugins").add(ColumnOptionPlugin.id, ColumnOptionPlugin);
