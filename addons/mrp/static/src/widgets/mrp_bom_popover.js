import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { PopoverComponent, PopoverWidgetField, popoverWidgetField } from "@stock/widgets/popover_widget";

class MrpBomPopover extends PopoverComponent {
    static template = "mrp.bomPopover";
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async _openBomOverview() {
        return this.actionService.doAction("mrp.action_report_mrp_bom", {
            additionalContext: {
                active_id: this.props.bom_id,
                active_model: "mrp.bom",
                mode: "forecast",
            },
        });
    }

    async goToAction(id, model) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
            context: { active_id: id },
        });
    }
}

class MrpBomPopoverField extends PopoverWidgetField {
    static template = "mrp.MrpBomPopoverField";
    static components = {
        Popover: MrpBomPopover,
    };
    setup() {
        super.setup();
        this.popover = usePopover(this.constructor.components.Popover, { position: useService("ui").isSmall ? "top" : "right" });
    }

    showPopup(ev) {
        this.jsonValue = JSON.parse(this.props.record.data[this.props.name] || "{}");
        super.showPopup(ev);
    }
}

registry.category("fields").add("mrp_bom_popover", {
    ...popoverWidgetField,
    component: MrpBomPopoverField,
});
