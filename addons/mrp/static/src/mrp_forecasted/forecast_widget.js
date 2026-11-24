import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, t, useProps } from "@odoo/owl";
import { formatFloat } from "@web/views/fields/formatters";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ForecastPopover extends Component {
    static template = "mrp.ForecastPopover";
    props = useProps({
        record: t.object(),
        infos: t.object(),
        close: t.function(),
    });

    setup() {
        this.actionService = useService("action");
        this.format = (value, digits) => formatFloat(value, { digits });
    }

    get readyToProduceClasses() {
        if (this.props.infos.ready_to_produce == 0) {
            return "text-danger";
        }
        if (this.props.infos.ready_to_produce == this.props.infos.quantity) {
            return "text-success";
        }
        return "";
    }

    async openForecast() {
        this.actionService.doAction("stock.stock_forecasted_product_product_action", {
            additionalContext: {
                active_model: "product.product",
                active_id: this.props.record.data.product_id.id,
                warehouse_id: this.props.infos.warehouse_id,
            },
        });
    }
}

export class ForecastWidget extends Component {
    static components = { Popover: ForecastPopover };
    static template = "mrp.ForecastWidget";
    props = useProps(standardWidgetProps);

    setup() {
        this.popover = usePopover(this.constructor.components.Popover, { position: "top" });
        this.orm = useService("orm");
    }

    async showPopup(ev) {
        const target = ev.currentTarget;
        const { data } = this.props.record;
        if (!data.id) {
            return;
        }
        const infos = await this.orm.call("mrp.production", "get_forecast_infos", [data.id]);
        this.popover.open(target, {
            record: this.props.record,
            infos,
        });
    }
}

export const forecastWidget = {
    component: ForecastWidget,
    fieldDependencies: [{ name: "forecasted_issue", type: "boolean" }],
};
registry.category("view_widgets").add("mrp_forecast_widget", forecastWidget);
