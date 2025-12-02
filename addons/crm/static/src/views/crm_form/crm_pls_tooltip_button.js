import { Component, status } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { localization } from "@web/core/l10n/localization";
import { registry } from '@web/core/registry';
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";


export class CrmPlsTooltip extends Component {
    static props = {
        close: { optional: true, type: Function },
        dashArrayVals: {type: String},
        low3Data: { optional: true, type: Object },
        probability: { type: Number },
        teamName: { optional: true, type: String },
        top3Data: { optional: true, type: Object },
    };
    static template = "crm.PlsTooltip";
}


export class CrmPlsTooltipButton extends Component {
    static template = "crm.PlsTooltipButton";
    static props = {...standardWidgetProps};

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.popover = usePopover(CrmPlsTooltip, {
            popoverClass: 'mt-2 me-2',
            position: "bottom-start",
        });
    }

    async onClickPlsTooltipButton(ev) {
        const tooltipButtonEl = ev.currentTarget;
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            // Apply pending changes. They may change probability
            await this.props.record.save();
            if (status(this) === "destroyed" || !this.props.record.resId) {
                return;
            }

            // This recomputes probability, and returns all tooltip data
            const tooltipData = await this.orm.call(
                "crm.lead",
                "prepare_pls_tooltip_data",
                [this.props.record.resId]
            );
            // Update the form
            await this.props.record.load();

            // Hard set wheel dimensions, see o_crm_pls_tooltip_wheel in scss and xml
            const progressWheelPerimeter = 2 * Math.PI * 25;
            const progressBarDashLength = progressWheelPerimeter * tooltipData.probability / 100.0;
            const progressBarDashGap = progressWheelPerimeter - progressBarDashLength;
            let dashArrayVals = progressBarDashLength + ' ' + progressBarDashGap;
            if (localization.direction === "rtl") {
                dashArrayVals = 0 + ' ' + 0.5 * progressWheelPerimeter + ' ' + dashArrayVals;
            }
            this.popover.open(tooltipButtonEl, {
                'dashArrayVals': dashArrayVals,
                'low3Data': tooltipData.low_3_data,
                'probability': tooltipData.probability,
                'teamName': tooltipData.team_name,
                'top3Data': tooltipData.top_3_data,
            });
        }
    }
}

registry.category("view_widgets").add("pls_tooltip_button", {
    component: CrmPlsTooltipButton
});
