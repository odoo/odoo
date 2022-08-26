/** @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

export class JsonPpopOver extends Component {
    setup() {
        this.props = { ...this.props, ...JSON.parse(this.props.value) };
    }
}

JsonPpopOver.displayName = _lt("Json Popup");
JsonPpopOver.supportedTypes = ["char"];

export class PopOverLeadDays extends JsonPpopOver {
    setup() {
        super.setup();
        const user = useService("user");
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
            ? `${this.props[field]} ${this.props.product_uom_name}`
            : this.props[field];
    }
}

PopOverLeadDays.template = "stock.leadDaysPopOver";

export class ReplenishmentHistoryWidget extends JsonPpopOver {}
ReplenishmentHistoryWidget.template = "stock.replenishmentHistory";

registry.category("fields").add("lead_days_widget", PopOverLeadDays);
registry.category("fields").add("replenishment_history_widget", ReplenishmentHistoryWidget);
