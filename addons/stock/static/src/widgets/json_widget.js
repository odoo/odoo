/** @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, onWillUpdateProps } = owl;

export class JsonPopOver extends Component {
    
    setup(){
        this.jsonValue = JSON.parse(this.props.value);
        onWillUpdateProps(nextProps => {
            this.jsonValue = JSON.parse(nextProps.value);
        });
    }
}

JsonPopOver.displayName = _lt("Json Popup");
JsonPopOver.supportedTypes = ["char"];

export class PopOverLeadDays extends JsonPopOver {
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
            ? `${this.jsonValue[field]} ${this.jsonValue.product_uom_name}`
            : this.jsonValue[field];
    }
}

PopOverLeadDays.template = "stock.leadDays";

export class ReplenishmentHistoryWidget extends JsonPopOver {}
ReplenishmentHistoryWidget.template = "stock.replenishmentHistory";

registry.category("fields").add("lead_days_widget", PopOverLeadDays);
registry.category("fields").add("replenishment_history_widget", ReplenishmentHistoryWidget);
