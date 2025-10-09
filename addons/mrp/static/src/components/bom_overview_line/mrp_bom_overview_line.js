import { useService } from "@web/core/utils/hooks";
import { formatFloat, formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { Component } from "@odoo/owl";

export class BomOverviewLine extends Component {
    static template = "mrp.BomOverviewLine";
    static props = {
        isFolded: { type: Boolean, optional: true },
        showOptions: {
            type: Object,
            shape: {
                mode: String,
                uom: Boolean,
            },
        },
        currentWarehouseId: { type: Number, optional: true },
        data: Object,
        precision: Number,
        toggleFolded: { type: Function, optional: true },
    };
    static defaultProps = {
        isFolded: true,
        toggleFolded: () => {},
    };

    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this.formatFloat = formatFloat;
        this.formatFloatTime = formatFloatTime;
        this.formatMonetary = (val) => formatMonetary(val, { currencyId: this.data.currency_id });
    }

    //---- Handlers ----

    async goToRoute(routeType) {
        if (routeType == "manufacture") {
            return this.goToAction(this.data.bom_id, "mrp.bom");
        }
    }

    async goToAction(id, model) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
            context: {
                active_id: id,
            },
        });
    }

    async goToForecast() {
        const action = await this.ormService.call(
            this.data.link_model,
            this.forecastAction,
            [[this.data.link_id]],
        );
        action.context = {
            active_model: this.data.link_model,
            active_id: this.data.link_id,
        };
        if (this.props.currentWarehouseId) {
            action.context["warehouse_id"] = this.props.currentWarehouseId;
        }
        return this.actionService.doAction(action);
    }

    //---- Getters ----

    get data() {
        return this.props.data;
    }

    get precision() {
        return this.props.precision;
    }

    get identifier() {
        return `${this.data.type}_${this.data.index}`;
    }

    get hasComponents() {
        return this.data.components && this.data.components.length > 0;
    }

    get hasOperations() {
        return this.data.operations && this.data.operations.length > 0;
    }

    get hasQuantity() {
        return this.data.is_storable && this.data.hasOwnProperty('quantity_available') && this.data.quantity_available !== false;
    }

    get hasLeadTime() {
        return this.data.hasOwnProperty('lead_time') && this.data.lead_time !== false;
    }

    get hasFoldButton() {
        return this.data.level > 0 && (this.hasComponents || this.hasOperations);
    }

    get marginMultiplicator() {
        return this.data.level - (this.hasFoldButton ? 1 : 0);
    }

    get forecastMode() {
        return this.props.showOptions.mode == "forecast";
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get availabilityColorClass() {
        // For first line, another rule applies : green if doable now, red otherwise.
        if (this.data.hasOwnProperty('components_available')) {
            if (this.data.components_available && this.data.availability_state != 'unavailable') {
                return "text-success";
            } else {
                return "text-danger";
            }
        }
        switch (this.data.availability_state) {
            case "available":
                return "text-success";
            case "expected":
                return "text-warning";
            case "unavailable":
                return "text-danger";
            default:
                return "";
        }
    }

    get forecastAction() {
        switch (this.data.link_model) {
            case "product.product":
                return "action_product_forecast_report";
            case "product.template":
                return "action_product_tmpl_forecast_report";
        }
    }

    get statusBackgroundClass() {
        if(this.data.index == "0") {
            return "text-bg-info";
        }
        return "text-bg-danger";
    }
}
