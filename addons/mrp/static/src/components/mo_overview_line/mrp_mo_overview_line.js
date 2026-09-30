import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { formatFloat, formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { getStateDecorator } from "./mo_overview_colors";
import { SHOW_OPTIONS } from "../mo_overview_display_filter/mrp_mo_overview_display_filter";

export class MoOverviewLine extends Component {
    static props = {
        data: {
            type: Object,
            shape: {
                level: Number,
                index: { type: String, optional: true },
                id: { type: Number, optional: true },
                model: { type: String, optional: true },
                name: String,
                product_model: { type: String, optional: true },
                product: { type: String, optional: true },
                product_id: { type: Number, optional: true },
                state: { type: String, optional: true },
                formatted_state: { type: String, optional: true },
                has_bom: { type: Boolean, optional: true },
                quantity: Number,
                replenish_quantity: { type: Number, optional: true },
                uom: { type: String, optional: true },
                uom_name: { type: String, optional: true },
                uom_precision: { type: Number, optional: true },
                quantity_free: { type: [Number, Boolean], optional: true },
                quantity_on_hand: { type: [Number, Boolean], optional: true },
                quantity_reserved: { type: Number, optional: true },
                receipt: {
                    type: Object,
                    shape: {
                        display: String,
                        type: String,
                        decorator: [String, Boolean],
                        date: [String, Boolean],
                    },
                    optional: true,
                },
                unit_cost: { type: Number, optional: true },
                mo_cost: { type: [Number, Boolean], optional: true },
                mo_cost_decorator: { type: [String, Boolean], optional: true },
                bom_cost: { type: [Number, Boolean], optional: true },
                real_cost: { type: [Number, Boolean], optional: true },
                real_cost_decorator: { type: [String, Boolean], optional: true },
                currency_id: Number,
                currency: { type: String, optional: true },
                production_id: { type: Number, optional: true },
            },
        },
        showOptions: SHOW_OPTIONS,
        hasFoldButton: { type: Boolean, optional: true },
        isFolded: { type: Boolean, optional: true },
        toggleFolded: { type: Function, optional: true },
    };

    static template = "mrp.MoOverviewLine";

    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this.formatFloat = (val) => formatFloat(val, { digits: [false, this.data.uom_precision || undefined] });
        this.formatFloatTime = formatFloatTime;
        this.formatMonetary = (val) => formatMonetary(val, { currencyId: this.data.currency_id });
    }

    //---- Handlers ----

    async openForm() {
        const model = this.data.level === 0 ? this.data.product_model : this.data.model;
        const id = this.data.level === 0 ? this.data.product_id : this.data.id;
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

    async openForecast() {
        const action = await this.ormService.call(
            this.data.product_model,
            this.forecastAction,
            [[this.data.product_id]],
        );
        action.context = {
            active_model: this.data.product_model,
            active_id: this.data.product_id,
        };
        return this.actionService.doAction(action);
    }

    async openReplenish() {
        return this.actionService.doAction("stock.action_product_replenish", {
            additionalContext: { default_product_id: this.data.product_id, default_quantity: this.data.replenish_quantity || this.data.quantity },
            onClose: (closeInfo) => {
                if (closeInfo?.done) {
                    // Trigger the reload only if a replenishment was done.
                    this.env.overviewBus.trigger("reload");
                }
            },
        });
    }

    async openWorkorder() {
        return this.actionService.doAction({
            name: this.data.name,
            type: "ir.actions.act_window",
            res_model: "mrp.workorder",
            views: [[false, "list"]],
            context: {
                search_default_ready: true,
                search_default_waiting: true,
                search_default_progress: true,
                search_default_blocked: true,
                search_default_name: this.data.name,
                search_default_production_id: this.data.production_id,
            },
        });
    }

    //---- Helpers ----

    getColorClass(decorator) {
        return decorator ? `text-${decorator}` : "";
    }

    hasQuantity(keyName) {
        return this.data.hasOwnProperty(keyName) && this.data[keyName] !== false;
    }

    //---- Getters ----

    get data() {
        return this.props.data;
    }

    get stateDecorator() {
        return getStateDecorator(this.data.model, this.data.state);
    }

    get formattedQuantity() {
        if (this.data.model === "mrp.workorder") {
            return this.formatFloatTime(this.data.quantity);
        }
        return this.formatFloat(this.data.quantity);
    }

    get hasFoldButton() {
        return false;
    }

    get marginMultiplicator() {
        return this.data.level - (this.props.hasFoldButton ? 1 : 0);
    }

    get foldButtonTitle() {
        return this.props.isFolded ? _t("Unfold") : _t("Fold");
    }

    get forecastAction() {
        switch (this.data.product_model) {
            case "product.product":
                return "action_product_forecast_report";
            case "product.template":
                return "action_product_tmpl_forecast_report";
        }
    }
}
