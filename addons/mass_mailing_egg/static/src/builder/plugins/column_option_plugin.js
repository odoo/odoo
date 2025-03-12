import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";
import { LAYOUT_COLUMN } from "@html_builder/utils/option_sequence";

class ColumnOptionPlugin extends Plugin {
    static id = "columnPlugin";
    selector = ".col-lg";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            withSequence(LAYOUT_COLUMN, {
                OptionComponent: BorderConfigurator,
                selector: this.selector,
                props: {
                    label: _t("Border")
                }
            }),
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("mass_mailing-plugins").add(ColumnOptionPlugin.id, ColumnOptionPlugin);
