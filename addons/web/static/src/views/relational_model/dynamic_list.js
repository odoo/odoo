/* @odoo-module */

import { DataPoint } from "./datapoint";
import { session } from "@web/session";

export class DynamicList extends DataPoint {
    setup(params) {
        super.setup(params);
        this.orderBy = params.orderBy || [];
        this.domain = params.domain;
        this.groupBy = [];
        this.limit = params.limit || 80;
        this.offset = params.offset || 0;
        this.count = params.data.length;
        this.isDomainSelected = false;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get selection() {
        return this.records.filter((r) => r.selected);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    async archive(isSelected) {
        return this.model.mutex.exec(() => this._toggleArchive(isSelected, true));
    }

    canResequence() {
        return false;
    }

    /**
     * @param {boolean} [isSelected]
     * @returns {Promise<number[]>}
     */
    async getResIds(isSelected) {
        let resIds;
        if (isSelected) {
            if (this.isDomainSelected) {
                resIds = await this.model.orm.search(this.resModel, this.domain, {
                    limit: session.active_ids_limit,
                    context: this.context,
                });
            } else {
                resIds = this.selection.map((r) => r.resId);
            }
        } else {
            resIds = this.records.map((r) => r.resId);
        }
        return resIds;
    }

    // TODO: keep this??
    selectDomain(value) {
        this.isDomainSelected = value;
    }

    async unarchive(isSelected) {
        return this.model.mutex.exec(() => this._toggleArchive(isSelected, false));
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _toggleArchive(isSelected, state) {
        const method = state ? "action_archive" : "action_unarchive";
        const context = this.context;
        const resIds = await this.getResIds(isSelected);
        const action = await this.model.orm.call(this.resModel, method, [resIds], { context });
        if (action && Object.keys(action).length) {
            this.model.action.doAction(action, { onClose: () => this._load() });
        } else {
            return this._load();
        }
    }
}
