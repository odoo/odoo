import { useEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { AccountProductCatalogSearchPanel } from "@account/components/product_catalog/search/search_panel";
import { TimePeriodSelectionField } from "./time_period_selection_fields";
import { formatMonetary } from "@web/views/fields/formatters";
import { clamp } from "@web/core/utils/numbers";

export class PurchaseSuggestCatalogSearchPanel extends AccountProductCatalogSearchPanel {
    static template = "purchase_stock.ProductCatalogSearchPanel";
    static components = { TimePeriodSelectionField };
    static basedOnOptions = [
        ["actual_demand", _t("Forecasted")],
        ["one_week", _t("Last 7 days")],
        ["30_days", _t("Last 30 days")],
        ["three_months", _t("Last 3 months")],
        ["one_year", _t("Last 12 months")],
        ["last_year", _t("Same month last year")],
        ["last_year_m_plus_1", _t("Next month last year")],
        ["last_year_m_plus_2", _t("After next month last year")],
        ["last_year_quarter", _t("Last year quarter")],
    ];

    setup() {
        super.setup();
        this.suggest = useEnv().suggest;
        this.toggleSuggest = useEnv().toggleSuggest;
        this.debouncedReloadKanban = useEnv().debouncedReloadKanban;
        this.reloadKanban = useEnv().reloadKanban;
        this.addAllProducts = useEnv().addAllProducts;
        this.displaySuggest = this.suggest.poState === "draft";
        this.tooltipTitle = _t(
            "Get recommendations of products to purchase at %(vendorName)s based on stock on hand, incoming quantities, " +
                "and expected sales volumes.\n\n Set a reference period to estimate sales, and use the percentage " +
                "to take into account seasonality and the increase/decrease of business.",
            { vendorName: this.suggest.vendorName }
        );
    }
    onDaysInput(ev) {
        const value = parseInt(ev.target.value, 10) || 0;
        const boundedVal = clamp(value, 0, 999); // 999 because input is 3 digits wide
        this.suggest.numberOfDays = boundedVal;
        ev.target.value = boundedVal;
        this.debouncedReloadKanban();
    }
    onPercentFactorInput(ev) {
        const value = parseInt(ev.target.value, 10) || 0;
        const boundedVal = clamp(value, 0, 999); // 999 because input is 3 digits wide
        this.suggest.percentFactor = boundedVal;
        ev.target.value = boundedVal;
        this.debouncedReloadKanban();
    }
    get estimatedSuggestPrice() {
        const { currencyId, digits } = this.suggest;
        return formatMonetary(this.suggest.totalEstimatedPrice, { currencyId, digits });
    }
    get timePeriodProps() {
        return {
            name: "based_on",
            required: true,
            record: {
                data: { based_on: this.suggest.basedOn },
                fields: { based_on: { selection: this.constructor.basedOnOptions } },
            },
            onChange: (val) => {
                this.suggest.basedOn = val;
                this.reloadKanban();
            },
        };
    }

    /* Emulate the behavior of input click from standard forms, list ... on custom inputs */
    selectAllOnClick(ev) {
        const el = ev.currentTarget;
        if (el.disabled || el.readOnly) {
            return;
        }
        ev.preventDefault();
        el.focus();
        el.select();
    }
}
