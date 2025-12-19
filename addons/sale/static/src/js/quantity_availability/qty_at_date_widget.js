import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, onWillRender } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";

export class QtyAtDatePopover extends Component {
    static template = "sale.QtyAtDatePopover";
    static props = {
        record: Object,
        calcData: Object,
        close: Function,
    };
    setup() {
        this.actionService = useService("action");
    }

    get forecastedLabel() {
        return _t("Forecasted Stock");
    }

    get availableLabel() {
        return _t("Available");
    }
}

export class QtyAtDateWidget extends Component {
    static components = { Popover: QtyAtDatePopover };
    static template = "sale.QtyAtDate";
    static props = { ...standardWidgetProps };
    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.orm = useService("orm");
        this.calcData = {};
        onWillRender(() => {
            this.initCalcData();
        });
    }

    async initCalcData() {
        // Computes the color of the chart icon representing the widget
        const { data } = this.props.record;
        const leftToDeliver = data.product_uom_qty - data.qty_delivered;

        this.calcData.forecasted_issue = "";
        if (data.qty_available_today < leftToDeliver) {
            this.calcData.forecasted_issue = "text-danger";
        } else if (data.virtual_available_at_date < 0) {
            this.calcData.forecasted_issue = "text-warning"; // Enough on hand NOW to fullfill not at delivery date
        }
    }

    updateCalcData() {
        // popup specific data
        const { data } = this.props.record;
        if (data.scheduled_date) {
            this.calcData.delivery_date = formatDateTime(data.scheduled_date, {
                format: localization.dateFormat,
            });
        }
    }

    async showPopup(ev) {
        const target = ev.currentTarget;
        this.updateCalcData();
        this.popover.open(target, {
            record: this.props.record,
            calcData: this.calcData,
        });
    }
}

export const qtyAtDateWidget = {
    component: QtyAtDateWidget,
    fieldDependencies: [
        { name: "display_qty_widget", type: "boolean" },
        { name: "qty_available_today", type: "float" },
        { name: "scheduled_date", type: "datetime" },
        { name: "virtual_available_at_date", type: "float" },
    ],
};
registry.category("view_widgets").add("simple_qty_at_date_widget", qtyAtDateWidget);
