import { t, usePlugin, useProps } from "@odoo/owl";
import {
    PopoverComponent,
    PopoverWidgetField,
    popoverWidgetField,
} from "@stock/widgets/popover_widget";
import { registry } from "@web/core/registry";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useService } from "@web/core/utils/hooks";

class MrpBomPopover extends PopoverComponent {
    static template = "mrp.bomPopover";

    mrpProps = useProps({
        final_product_name: t.string().optional(),
        bom_id: t.any(),
        component: t.any(),
        component_id: t.any(),
        route_name: t.any(),
        route_detail: t.any(),
        route_type: t.any(),
        route_id: t.any(),
        delay: t.any(),
    });

    setup() {
        super.setup();

        this.actionService = useService("action");
    }

    async _openBomOverview() {
        return this.actionService.doAction("mrp.action_report_mrp_bom", {
            additionalContext: {
                active_id: this.mrpProps.bom_id,
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

    uiPlugin = usePlugin(UIPlugin);

    getPosition() {
        return this.uiPlugin.isSmall() ? "top" : "right";
    }
}

registry.category("fields").add("mrp_bom_popover", {
    ...popoverWidgetField,
    component: MrpBomPopoverField,
});
