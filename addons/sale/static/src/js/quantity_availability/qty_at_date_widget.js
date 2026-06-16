import { formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, computed } from "@odoo/owl";
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

    calcData = computed(() => this.initCalcData());

    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.orm = useService("orm");
    }

    initCalcData() {
        // Computes the color of the chart icon representing the widget
        const calcData = {};
        const { data } = this.props.record;
        calcData.leftToDeliver = data.product_uom_qty - data.qty_delivered;
        calcData.forecasted_issue = data.virtual_available_at_date < calcData.leftToDeliver ? "text-danger" : "";
        return calcData;
    }

    updateCalcData(calcData) {
        // popup specific data
        const { data } = this.props.record;
        if (data.scheduled_date) {
            calcData.delivery_date = formatDateTime(data.scheduled_date, {
                format: localization.dateFormat,
            });
        }
    }

    async showPopup(ev) {
        const target = ev.currentTarget;
        const calcData = { ...this.calcData() };
        this.updateCalcData(calcData);
        this.popover.open(target, {
            record: this.props.record,
            calcData,
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
