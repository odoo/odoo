/** @odoo-module **/

import { registry } from "@web/core/registry";
import { LazyColumnLoading } from "@stock/widgets/lazy_availability_widget/lazy_availability_widget";
import { _t } from "@web/core/l10n/translation";

export class MrpLazyColumnLoading extends LazyColumnLoading {
    setup() {
        super.setup();
        this.model = 'mrp.production';
        this.fieldName = "components_availability";
        this.componentStateField = "components_availability_state";
        this.reservationStateField = "reservation_state";
    }
}

export const mrpLazyColumnLoading = {
    component: MrpLazyColumnLoading,
    label: _t("Components Availability"),
};

registry.category("view_widgets").add("mrp_lazy_column_widget", mrpLazyColumnLoading);
