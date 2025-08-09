/** @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useBus, useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { DateTimeInput } from '@web/core/datetime/datetime_input';
import { Component, useState, onWillStart, markup, xml } from "@odoo/owl";

export class LunchCurrency extends Component {
    static template = "lunch.LunchCurrency";
    static props = ["currency", "amount"];

    get amount() {
        return parseFloat(this.props.amount).toFixed(2);
    }
}

export class LunchOrderLine extends Component {
    static template = "lunch.LunchOrderLine";
    static props = ["line", "currency", "onUpdateQuantity", "openOrderLine", "infos"];
    static components = {
        LunchCurrency,
    };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useState({ mobileOpen: false });
    }

    get line() {
        return this.props.line;
    }

    get canAdd(){
        let price = this.line.product[3]
        this.line.toppings.forEach((line) => price += line[3])
        const unpaid = parseFloat(this.props.infos.unpaid_subtotal)
        return this.canEdit && (this.props.infos.wallet_with_config - unpaid) >= price;
    }

    get canEdit() {
        return !['sent', 'confirmed'].includes(this.line.raw_state);
    }

    get badgeClass() {
        const mapping = {'new': 'warning', 'confirmed': 'success', 'sent': 'info', 'ordered': 'danger'};
        return mapping[this.line.raw_state];
    }

    get hasToppings() {
        return this.line.toppings.length !== 0;
    }

    async updateQuantity(increment) {
        await this.orm.call('lunch.order', 'update_quantity', [
            this.props.line.id,
            increment
        ]);

        await this.props.onUpdateQuantity();
    }
}

export class LunchAlert extends Component {
    static props = ["message"];
    static template = xml`<t t-out="message"/>`;
    get message() {
        return markup(this.props.message);
    }
}

export class LunchAlerts extends Component {
    static components = {
        LunchAlert,
    };
    static props = ["alerts"];
    static template = "lunch.LunchAlerts";
}

export class LunchUser extends Component {
    static components = {
        Many2XAutocomplete,
    };
    static props = ["username", "isManager", "onUpdateUser"];
    static template = "lunch.LunchUser";
    getDomain() {
        return [['share', '=', false]];
    }
}

export class LunchLocation extends Component {
    static components = {
        Many2XAutocomplete,
    };
    static props = ["location", "onUpdateLunchLocation"];
    static template = "lunch.LunchLocation";
    getDomain() {
        return [];
    }
}

export class LunchDashboard extends Component {
    static components = {
        LunchAlerts,
        LunchCurrency,
        LunchLocation,
        LunchOrderLine,
        LunchUser,
        Many2XAutocomplete,
    };
    static props = ["openOrderLine"];
    static template = "lunch.LunchDashboard";
    setup() {
        super.setup();
        this.state = useState({
            infos: {},
            date: new Date(),
        });

        useBus(this.env.bus, 'lunch_update_dashboard', () => this._fetchLunchInfos());
        onWillStart(async () => {
            await this._fetchLunchInfos()
            this.env.searchModel.updateLocationId(this.state.infos.user_location[0]);
        });
    }

    async lunchRpc(route, args = {}) {
        return await rpc(route, {
            ...args,
            context: user.context,
            user_id: this.env.searchModel.lunchState.userId,
        })
    }

    async _fetchLunchInfos() {
        this.state.infos = await this.lunchRpc('/lunch/infos');
    }

    async emptyCart() {
        await this.lunchRpc('/lunch/trash');
        await this._fetchLunchInfos();
    }

    get hasLines() {
        return this.state.infos.lines && this.state.infos.lines.length !== 0;
    }

    get canOrder() {
        return this.state.infos.raw_state === 'new';
    }

    get location() {
        return this.state.infos.user_location && this.state.infos.user_location[1];
    }

    async orderNow() {
        if (!this.canOrder) {
            return;
        }

        await this.lunchRpc('/lunch/pay');
        await this._fetchLunchInfos();
    }

    async onUpdateQuantity() {
        await this._fetchLunchInfos();
    }

    async onUpdateUser(value) {
        if (!value) {
            return;
        }
        this.env.searchModel.updateUserId(value[0].id);
        await this._fetchLunchInfos();
    }

    async onUpdateLunchLocation(value) {
        if (!value) {
            return;
        }

        await this.lunchRpc('/lunch/user_location_set', {
            location_id: value[0].id,
        });
        await this._fetchLunchInfos();
        this.env.searchModel.updateLocationId(value[0].id);
    }

    async onUpdateLunchTime(value) {
        if (value) {
            // Set time at 12:00
            this.state.date.setTime(value + 12 * 60 * 60 * 1000);
        } else {
            this.state.date.setTime(new Date());
        }
        this.env.searchModel.updateDate(this.state.date);
    }
}

LunchDashboard.components = {
    LunchAlerts,
    LunchCurrency,
    LunchLocation,
    LunchOrderLine,
    LunchUser,
    Many2XAutocomplete,
    DateTimeInput,
};
LunchDashboard.props = ["openOrderLine"];
LunchDashboard.template = 'lunch.LunchDashboard';
