import { useEnv, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ProductCatalogSearchPanel } from "@product/product_catalog/search/search_panel";
import { TimePeriodSelectionField } from "./time_period_selection_fields";

export class PurchaseSuggestCatalogSearchPanel extends ProductCatalogSearchPanel {
    static template = "purchase_stock.SearchPanel";
    static components = { TimePeriodSelectionField };

    setup() {
        super.setup();
        this.wizard = useState(useEnv().purchaseSuggestWizard);
        this.addAllProducts = useEnv().addAllProducts;
        this.tooltipTitle = _t(
            "Get recommendations of products to purchase at %(vendorName)s based on stock on hand, incoming quantities, " +
                "and expected sales volumes.\n\n Set a reference period to estimate sales, and use the percentage " +
                "to take into account seasonality and the increase/decrease of business.",
            { vendorName: this.wizard.vendorName }
        );
    }
    onDaysInput(ev) {
        this.wizard.numberOfDays = parseInt(ev.target.value, 10) || 0;
    }
    onPercentFactorInput(ev) {
        this.wizard.percentFactor = parseInt(ev.target.value, 10) || 0;
    }
    async onSuggestToggle() {
        this.wizard.suggestToggle.isOn = !this.wizard.suggestToggle.isOn;
        localStorage.setItem(
            "purchase_stock.suggest_toggle_state",
            JSON.stringify({ isOn: this.wizard.suggestToggle.isOn })
        );
    }
    get timePeriodProps() {
        return {
            name: "based_on",
            required: true,
            record: {
                data: { based_on: this.wizard.basedOn },
                fields: { based_on: { selection: this.wizard.basedOnOptions } },
            },
            onChange: (val) => {
                this.wizard.basedOn = val;
            },
        };
    }
}
