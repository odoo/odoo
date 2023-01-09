/** @odoo-module */

import { useBus, useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

const { Component, useState, onWillStart, markup, xml } = owl;

export class LunchCurrency extends Component {
    get amount() {
        return parseFloat(this.props.amount).toFixed(2);
    }
}
LunchCurrency.template = 'lunch.LunchCurrency';
LunchCurrency.props = ["currency", "amount"];

export class LunchOrderLine extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useState({ mobileOpen: false });
    }

    get line() {
        return this.props.line;
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
LunchOrderLine.template = 'lunch.LunchOrderLine';
LunchOrderLine.props = ["line", "currency", "onUpdateQuantity", "openOrderLine"];
LunchOrderLine.components = {
    LunchCurrency,
};

export class LunchAlert extends Component {
    get message() {
        return markup(this.props.message);
    }
}
LunchAlert.props = ["message"];
LunchAlert.template = xml`<t t-out="message"/>`

export class LunchAlerts extends Component {}
LunchAlerts.components = {
    LunchAlert,
}
LunchAlerts.props = ["alerts"];
LunchAlerts.template = 'lunch.LunchAlerts';

export class LunchUser extends Component {
    getDomain() {
        return [['share', '=', false]];
    }
}
LunchUser.components = {
    Many2XAutocomplete,
}
LunchUser.props = ["username", "isManager", "onUpdateUser"];
LunchUser.template = "lunch.LunchUser";

export class LunchLocation extends Component {
    getDomain() {
        return [];
    }
}
LunchLocation.components = {
    Many2XAutocomplete,
}
LunchLocation.props = ["location", "onUpdateLunchLocation"];
LunchLocation.template = "lunch.LunchLocation";

export class LunchDashboard extends Component {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.state = useState({
            infos: {},
        });

        useBus(this.env.bus, 'lunch_update_dashboard', () => this._fetchLunchInfos());
        onWillStart(async () => {
            await this._fetchLunchInfos()
            this.env.searchModel.updateLocationId(this.state.infos.user_location[0]);
        });
    }

    async lunchRpc(route, args = {}) {
        return await this.rpc(route, {
            ...args,
            context: this.user.context,
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
}
LunchDashboard.components = {
    LunchAlerts,
    LunchCurrency,
    LunchLocation,
    LunchOrderLine,
    LunchUser,
    Many2XAutocomplete,
};
LunchDashboard.props = ["openOrderLine"];
LunchDashboard.template = 'lunch.LunchDashboard';
