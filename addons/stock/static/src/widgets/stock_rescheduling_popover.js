/** @odoo-module native */
import {
    PopoverComponent,
    PopoverWidgetField,
    popoverWidgetField,
} from "@stock/widgets/popover_widget";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";

export class StockReschedulingPopoverComponent extends PopoverComponent {
    setup() {
        this.action = useService("action");
    }

    get precedingLabel() {
        return _t("Preceding operations:");
    }

    get plannedLabel() {
        return _t("Planned on %s.", this.props.date_delay_alert);
    }

    openElement(ev) {
        this.action.doAction({
            res_model: ev.currentTarget.getAttribute("element-model"),
            res_id: parseInt(ev.currentTarget.getAttribute("element-id"), 10),
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
        });
    }
}

export class StockReschedulingPopover extends PopoverWidgetField {
    static components = {
        Popover: StockReschedulingPopoverComponent,
    };
    static defaultColor = "text-danger";
    static defaultIcon = "fa-triangle-exclamation";

    showPopup(ev) {
        if (!this.jsonValue.late_elements?.length) {
            return;
        }
        super.showPopup(ev);
    }
}

registry.category("fields").add("stock_rescheduling_popover", {
    ...popoverWidgetField,
    component: StockReschedulingPopover,
});
