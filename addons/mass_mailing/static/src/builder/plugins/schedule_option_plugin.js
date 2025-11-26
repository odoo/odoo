import { AddProductOption } from "@html_builder/plugins/add_product_option";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class ScheduleAddProductOption extends AddProductOption {
    static id = "schedule_add_product_option";
    static defaultProps = {
        buttonLabel: _t("Add Activity"),
    };
}

registry
    .category("mass_mailing-options")
    .add(ScheduleAddProductOption.id, ScheduleAddProductOption);
