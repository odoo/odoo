import { props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { BomOverviewDisplayFilter } from "../bom_overview_display_filter/mrp_bom_overview_display_filter";

export const SHOW_OPTIONS = t.object({
    uom: t.boolean(),
    replenishments: t.boolean(),
    availabilities: t.boolean(),
    receipts: t.boolean(),
    unitCosts: t.boolean(),
    moCosts: t.boolean(),
    bomCosts: t.boolean(),
    realCosts: t.boolean(),
});

export class MoOverviewDisplayFilter extends BomOverviewDisplayFilter {
    props = props({
        showOptions: SHOW_OPTIONS,
        changeDisplay: t.function(),
        limited: t.boolean().optional(false),
        isProductionDraft: t.boolean().optional(false),
    });

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
