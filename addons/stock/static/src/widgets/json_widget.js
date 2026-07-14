/** @odoo-module */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { Component, onWillStart } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class JsonPopOver extends Component {
    static template = "";
    static props = {...standardFieldProps};
    get jsonValue() {
        return JSON.parse(this.props.record.data[this.props.name]);
    }
}

export const jsonPopOver = {
    component: JsonPopOver,
    displayName: _t("Json Popup"),
    supportedTypes: ["char"],
};

export class PopOverLeadDays extends JsonPopOver {
    static template = "stock.leadDays";
    setup() {
        super.setup();
        onWillStart(async () => {
            this.displayUOM = await user.hasGroup("uom.group_uom");
        });
    }

    get qtyForecast() {
        return this._formatQty("qty_forecast");
    }
    get qtyToOrder() {
        return this._formatQty("qty_to_order");
    }
    get productMaxQty() {
        return this._formatQty("product_max_qty");
    }
    get productMinQty() {
        return this._formatQty("product_min_qty");
    }

    _formatQty(field) {
        return this.displayUOM
            ? `${this.jsonValue[field]} ${this.jsonValue.product_uom_name}`
            : this.jsonValue[field];
    }
}


export const popOverLeadDays = {
    ...jsonPopOver,
    component: PopOverLeadDays,
};
registry.category("fields").add("lead_days_widget", popOverLeadDays);

export class ReplenishmentHistoryWidget extends JsonPopOver {
    static template = "stock.replenishmentHistory";
}

export const replenishmentHistoryWidget = {
    ...jsonPopOver,
    component: ReplenishmentHistoryWidget,
};

registry.category("fields").add("replenishment_history_widget", replenishmentHistoryWidget);
