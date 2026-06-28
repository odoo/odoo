import { AddProductOption } from "@html_builder/plugins/add_product_option";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { props, t } from "@odoo/owl";

export class ScheduleAddProductOption extends AddProductOption {
    static id = "schedule_add_product_option";
    // inlined from AddProductOption.props (still old-style)
    props = props({
        buttonApplyTo: t.string().optional(),
        productSelector: t.string().optional(),
        buttonLabel: t.string().optional(_t("Add Activity")),
    });
}

registry
    .category("mass_mailing-options")
    .add(ScheduleAddProductOption.id, ScheduleAddProductOption);
