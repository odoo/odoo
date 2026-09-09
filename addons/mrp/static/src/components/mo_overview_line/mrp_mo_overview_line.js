import { _t } from "@web/core/l10n/translation";
import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { formatFloat, formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { getStateDecorator } from "./mo_overview_colors";
import { SHOW_OPTIONS } from "../mo_overview_display_filter/mrp_mo_overview_display_filter";

export class MoOverviewLine extends Component {
    props = useProps({
        data: t.object({
            level: t.number(),
            index: t.string().optional(),
            id: t.number().optional(),
            model: t.string().optional(),
            name: t.string(),
            product_model: t.string().optional(),
            product: t.string().optional(),
            product_id: t.number().optional(),
            state: t.string().optional(),
            formatted_state: t.string().optional(),
            has_bom: t.boolean().optional(),
            quantity: t.number(),
            replenish_quantity: t.number().optional(),
            uom: t.string().optional(),
            uom_name: t.string().optional(),
            uom_precision: t.number().optional(),
            quantity_free: t.or([t.number(), t.boolean()]).optional(),
            quantity_on_hand: t.or([t.number(), t.boolean()]).optional(),
            quantity_reserved: t.number().optional(),
            receipt: t.object({
                display: t.string(),
                type: t.string(),
                decorator: t.or([t.string(), t.boolean()]),
                date: t.or([t.string(), t.boolean()]),
            }).optional(),
            unit_cost: t.number().optional(),
            mo_cost: t.or([t.number(), t.boolean()]).optional(),
            mo_cost_decorator: t.or([t.string(), t.boolean()]).optional(),
            bom_cost: t.or([t.number(), t.boolean()]).optional(),
            real_cost: t.or([t.number(), t.boolean()]).optional(),
            real_cost_decorator: t.or([t.string(), t.boolean()]).optional(),
            currency_id: t.number(),
            currency: t.string().optional(),
            production_id: t.number().optional(),
        }),
        showOptions: SHOW_OPTIONS,
        hasFoldButton: t.boolean().optional(),
        isFolded: t.boolean().optional(),
        toggleFolded: t.function().optional(),
    });

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
        if (this.data.model === "mrp.workorder" || !this.data.model) {
            return this.formatFloatTime(this.data.quantity, { unit: this.data.state ? "minutes" : "hours", showSeconds: true });
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
