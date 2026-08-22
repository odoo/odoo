import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class JsonPopOver extends Component {
    static template = "";
    static props = { ...standardFieldProps };
    get jsonValue() {
        return JSON.parse(this.props.record.data[this.props.name]);
    }
}

export const jsonPopOver = {
    component: JsonPopOver,
    displayName: _t("Json Popup"),
    supportedTypes: ["char"],
};

// --------------------------------------------------------------------------
// Lead Days
// --------------------------------------------------------------------------

export class PopOverLeadDays extends JsonPopOver {
    static template = "stock.leadDays";
}

export const popOverLeadDays = {
    ...jsonPopOver,
    component: PopOverLeadDays,
};
registry.category("fields").add("lead_days_widget", popOverLeadDays);

// --------------------------------------------------------------------------
// Update Button
// --------------------------------------------------------------------------

export class UpdateButton extends Component {
    static template = "stock.updateButton";
    static props = { ...standardFieldProps };

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async updateDailyDemand(ev) {
        if (this.props.record.data.based_on != "custom") {
            const daily = await this.orm.call("stock.replenishment.info", "get_daily_demand", [
                this.props.record.resId,
                this.props.record.data.based_on,
                this.props.record.data.percent_factor
            ]);
            this.props.record.update({
                'daily_demand': daily,
            });
            this.props.record.update({
                'based_on': this.props.record.data.based_on,
            });
        }
    }
}

export const updateButton = {
    component: UpdateButton,
}
registry.category("fields").add("update_demand_button", updateButton);
