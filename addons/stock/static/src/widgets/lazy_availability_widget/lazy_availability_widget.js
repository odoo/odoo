/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class LazyColumnLoading extends Component {
    static props = { ...standardWidgetProps };
    setup() {
        this.model = 'stock.picking';
        this.fieldName = "products_availability";
        this.componentStateField = "products_availability_state";
        this.reservationStateField = "state";
        this.state = useState({
            loading: true,
            value: {},
        });
        this.lazyLoading = useService("lazy_column_loading");

        onWillStart(() => {
            this.lazyLoading.call(this.props.record.resId, this.model, [
                this.fieldName,
                this.componentStateField,
                this.reservationStateField,
            ] ).then((value) => {
                this.state.value = value;
                this.state.loading = false;
            });
        });
    }

    get components_availability() {
        return this.state.value[this.fieldName] || "";
    }

    get decorator() {
        const state = this.state.value[this.componentStateField];
        const reservationState = this.state.value[this.reservationStateField];

        if (reservationState == "assigned" || state == "available") {
            return "text-success";
        }
        if (reservationState != "assigned" && (state == "available" || state == "expected")) {
            return "text-warning";
        }
        if (reservationState != "assigned" && (state == "late" || state == "unavailable")) {
            return "text-danger";
        }
        return "";
    }
}

LazyColumnLoading.template = "stock.LazyColumnLoading";

export const lazyColumnLoading = {
    component: LazyColumnLoading,
    label: _t("Components Availability"),
};

registry.category("view_widgets").add("lazy_column_widget", lazyColumnLoading);
