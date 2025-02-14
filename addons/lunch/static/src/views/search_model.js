import { Domain } from '@web/core/domain';
import { rpc } from "@web/core/network/rpc";
import { SearchModel } from '@web/search/search_model';
import { useState, onWillStart } from "@odoo/owl";
const { DateTime } = luxon;

export class LunchSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);

        this.lunchState = useState({
            locationId: false,
            userId: false,
            date: DateTime.now(),
        });

        onWillStart(async () => {
            const locationId = await rpc('/lunch/user_location_get', {});
            this.updateLocationId(locationId);
        });
    }

    exportState() {
        const state = super.exportState();
        state.locationId = this.lunchState.locationId;
        state.userId = this.lunchState.userId;
        return state;
    }

    _importState(state) {
        super._importState(...arguments);

        if (state.locationId) {
            this.lunchState.locationId = state.locationId;
        }
        if (state.userId) {
            this.lunchState.userId = state.userId;
        }
    }

    updateUserId(userId) {
        this.lunchState.userId = userId;
        this._notify();
    }

    updateLocationId(locationId) {
        this.lunchState.locationId = locationId;
        this._notify();
    }

    updateDate(date) {
        this.lunchState.date = date;
        const weekday = this.lunchState.date.toJSDate().getDay();
        const domain_key = ['available_on_sun', 'available_on_mon', 'available_on_tue', 'available_on_wed',
        'available_on_thu', 'available_on_fri', 'available_on_sat'][weekday];
        const filter = Object.values(this.searchItems).find(o => o['name'] === domain_key);
        this.deactivateGroup(filter.groupId)
        this.toggleSearchItem(filter.id);
        this._notify();
    }

    _getDomain(params = {}) {
        const domain = super._getDomain(params);

        if (!this.lunchState.locationId) {
            return domain;
        }
        const result = Domain.and([
            domain,
            [['is_available_at', '=', this.lunchState.locationId]]
        ]);
        return params.raw ? result : result.toList();
    }
}
