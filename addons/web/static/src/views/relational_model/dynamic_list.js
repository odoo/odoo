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
}
