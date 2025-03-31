/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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
                availabilities: Boolean,
                costs: Boolean,
                operations: Boolean,
                leadTimes: Boolean,
                uom: Boolean,
                attachments: Boolean,
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

    async goToAttachment() {
        return this.actionService.doAction({
            name: _t("Attachments"),
            type: "ir.actions.act_window",
            res_model: "product.document",
            domain: ['&', ["attached_on_mrp", "=", "bom"], '|',
                '&',["res_model", "=", "product.product"],["res_id", "in", [this.data.product_id]],
                '&',["res_model", "=", "product.template"],["res_id", "in", [this.data.product_template_id]]],
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            view_mode: "kanban,list,form",
            target: "current",
            context:{
                'bom_id': true,
                'default_res_id': this.data.product_id,
                'default_res_model': "product.product"
            }
        });
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
        return this.data.hasOwnProperty('quantity_available') && this.data.quantity_available !== false;
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

    get showAvailabilities() {
        return this.props.showOptions.availabilities;
    }

    get showCosts() {
        return this.props.showOptions.costs;
    }

    get showLeadTimes() {
        return this.props.showOptions.leadTimes;
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get showAttachments() {
        return this.props.showOptions.attachments;
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
}
