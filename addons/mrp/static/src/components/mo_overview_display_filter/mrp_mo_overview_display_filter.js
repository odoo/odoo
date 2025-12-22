/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";

export const SHOW_OPTIONS = {
    type: Object,
    shape: {
        uom: Boolean,
        replenishments: Boolean,
        availabilities: Boolean,
        receipts: Boolean,
        unitCosts: Boolean,
        moCosts: Boolean,
        bomCosts: Boolean,
        realCosts: Boolean,
    },
};

export class MoOverviewDisplayFilter extends BomOverviewDisplayFilter {
    static props = {
        showOptions: SHOW_OPTIONS,
        changeDisplay: Function,
        limited: { type: Boolean, optional: true },
        isProductionDraft: { type: Boolean, optional: true},
    };
    static defaultProps = {
        limited: false,
        isProductionDraft: false,
    };

    setup() {
        this.displayOptions = {
            unitCosts: _t("Unit Costs"),
            moCosts: _t("MO Costs"),
            bomCosts: _t("BoM Costs"),
        };
        if (!this.props.limited) {
            this.displayOptions = {
                ...this.displayOptions,
                replenishments: _t("Replenishments"),
                availabilities: _t("Availabilities"),
                receipts: _t("Receipts"),
            };
        }
        if (!this.props.isProductionDraft) {
            this.displayOptions = {
                ...this.displayOptions,
                realCosts: _t("Real Costs"),
            };
        }
    }
}
