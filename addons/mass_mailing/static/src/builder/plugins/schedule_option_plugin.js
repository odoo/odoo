import { BaseAddProductOption } from "@html_builder/plugins/add_product_option";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BEGIN } from "@html_builder/utils/option_sequence";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class MassMailingScheduleAddProductOption extends BaseAddProductOption {
    static selector = ".s_schedule:has(table)";
    productSelector = "tr";
    buttonLabel = _t("Add Activity");
}

export class ScheduleOptionPlugin extends Plugin {
    static id = "mass_mailing.ScheduleOptionPlugin";
    resources = {
        builder_options: [withSequence(BEGIN, MassMailingScheduleAddProductOption)],
    };
}

registry.category("mass_mailing-plugins").add(ScheduleOptionPlugin.id, ScheduleOptionPlugin);
