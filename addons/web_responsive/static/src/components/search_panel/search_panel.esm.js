/** @odoo-module **/
/* Copyright 2021 ITerra - Sergey Shebanin
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import SearchPanel from "@web/legacy/js/views/search_panel";
import {deviceContext} from "@web_responsive/components/ui_context.esm";
import {patch} from "web.utils";

// Patch search panel to add functionality for mobile view
patch(SearchPanel.prototype, "web_responsive.SearchPanelMobile", {
    setup() {
        this._super();
        this.state.mobileSearch = false;
        this.ui = deviceContext;
    },
    getActiveSummary() {
        const selection = [];
        for (const filter of this.model.get("sections")) {
            let filterValues = [];
            if (filter.type === "category") {
                if (filter.activeValueId) {
                    const parentIds = this._getAncestorValueIds(
                        filter,
                        filter.activeValueId
                    );
                    filterValues = [...parentIds, filter.activeValueId].map(
                        (valueId) => filter.values.get(valueId).display_name
                    );
                }
            } else {
                let values = [];
                if (filter.groups) {
                    values = [
                        ...[...filter.groups.values()].map((g) => g.values),
                    ].flat();
                }
                if (filter.values) {
                    values = [...filter.values.values()];
                }
                filterValues = values
                    .filter((v) => v.checked)
                    .map((v) => v.display_name);
            }
            if (filterValues.length) {
                selection.push({
                    values: filterValues,
                    icon: filter.icon,
                    color: filter.color,
                    type: filter.type,
                });
            }
        }
        return selection;
    },
});
