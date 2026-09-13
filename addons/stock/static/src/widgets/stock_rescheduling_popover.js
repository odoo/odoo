import { computed } from "@odoo/owl";
import {
    PopoverComponent,
    PopoverWidgetField,
    popoverWidgetField,
} from "@stock/widgets/popover_widget";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class StockRescheculingPopoverComponent extends PopoverComponent {
    setup() {
        super.setup();

        this.action = useService("action");
    }

    openElement(ev) {
        this.action.doAction({
            res_model: ev.currentTarget.getAttribute("element-model"),
            res_id: parseInt(ev.currentTarget.getAttribute("element-id")),
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
        });
    }
}

export class StockRescheculingPopover extends PopoverWidgetField {
    static components = {
        Popover: StockRescheculingPopoverComponent,
    };

    color = computed(() => this.jsonValue().color || "text-danger");
    icon = computed(() => this.jsonValue().icon || "warning");

    showPopup(ev) {
        if (!this.jsonValue().late_elements) {
            return;
        }
        super.showPopup(ev);
    }
}

registry.category("fields").add("stock_rescheduling_popover", {
    ...popoverWidgetField,
    component: StockRescheculingPopover,
});
