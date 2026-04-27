/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";
import { useState } from "@odoo/owl";

export class MrpDisplaySearchModel extends SearchModel {
    setup(services, args) {
        super.setup(services);
        this.state = useState({
            workorderFilters: [
                {
                    name: "ready",
                    string: _t("Ready"),
                    isActive: !args.show_progress_workorders,
                },
                {
                    name: "progress",
                    string: _t("In Progress"),
                    isActive: !args.show_ready_workorders,
                },
                {
                    name: "waiting",
                    string: _t("Waiting"),
                    isActive: false,
                },
                {
                    name: "pending",
                    string: _t("Pending"),
                    isActive: false,
                },
                {
                    name: "done",
                    string: _t("Finished"),
                    isActive: false,
                },
            ],
        });
        this.workorders = true;
    }

    _getFacets() {
        // Add workorder filter facet to the search bar if applicable
        const facets = super._getFacets();
        if (this.workorders && !facets.some((f) => f.type === "favorite")) {
            const values = this.state.workorderFilters.reduce(
                (acc, i) => (i.isActive ? [...acc, i.string] : acc),
                []
            );
            if (values.length) {
                facets.push({
                    groupId: 0,
                    type: "filter",
                    values: values,
                    separator: "or",
                    icon: "fa fa-filter",
                    color: "info",
                });
            }
        }
        return facets;
    }

    _getIrFilterDescription(params = {}) {
        // Save workorder filters in favorite context
        const { irFilter, preFavorite } = super._getIrFilterDescription(params);
        if (this.workorders) {
            const activeFilterIds = this.state.workorderFilters.reduce(
                (acc, i) => (i.isActive ? [...acc, i.name] : acc),
                []
            );
            irFilter.context.wo_active_filters = activeFilterIds;
            preFavorite.context.wo_active_filters = activeFilterIds;
        }
        return { preFavorite, irFilter };
    }

    toggleSearchItem(searchItemId) {
        // Retrieve saved workorder filters from context or reset WO filters when enabling/disabling a favorite respectively
        const { type, context } = this.searchItems[searchItemId];
        if (this.workorders && type === "favorite") {
            const { wo_active_filters } = context;
            const removeFavorite =
                !wo_active_filters ||
                this.query.some((queryElem) => queryElem.searchItemId === searchItemId);
            for (const filter of this.state.workorderFilters) {
                filter.isActive = !removeFavorite && wo_active_filters.includes(filter.name);
            }
        }
        return super.toggleSearchItem(searchItemId);
    }

    async deleteFavorite(favoriteId) {
        // Reset WO filters when deleting a currently enabled favorite
        if (
            this.workorders &&
            this.query.some((queryElem) => queryElem.searchItemId === favoriteId)
        ) {
            for (const filter of this.state.workorderFilters) {
                filter.isActive = false;
            }
        }
        return super.deleteFavorite(favoriteId);
    }

    setWorkcenterFilter(workcenters) {
        const filter = Object.values(this.searchItems).find(
            (si) => si.name === "shop_floor_this_station"
        );
        if (!filter) {
            return; // Avoid crashing when 'This Station' filter not installed.
        }
        filter.domain =
            "['|', ['workorder_ids.workcenter_id.id', 'in', [" +
            workcenters.map((wc) => wc.id).join(",") +
            "]], ['workorder_ids', '=', False]]";
        if (this.query.find((queryElem) => queryElem.searchItemId === filter.id)) {
            this._notify();
        }
    }
}
