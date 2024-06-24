import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class TooltipLabel extends Component {
    static template = "pos_self_order.TooltipLabel";
    static props = { ...standardWidgetProps };
    get tooltipInfo() {
        return JSON.stringify({ tooltip: _t("Only works for kiosk and mobile") });
    }
}

export const tooltipLabel = {
    component: TooltipLabel,
    extractProps: ({ attrs }) => {
        return {};
    },
};

registry.category("view_widgets").add("available_between_label", tooltipLabel);
