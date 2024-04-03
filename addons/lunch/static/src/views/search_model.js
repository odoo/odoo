/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

import { Domain } from '@web/core/domain';
import { SearchModel } from '@web/search/search_model';

const { useState, onWillStart } = owl;


export class LunchSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);

        this.rpc = useService('rpc');
        this.lunchState = useState({
            locationId: false,
            userId: false,
        });

        onWillStart(async () => {
            const locationId = await this.rpc('/lunch/user_location_get', {});
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
