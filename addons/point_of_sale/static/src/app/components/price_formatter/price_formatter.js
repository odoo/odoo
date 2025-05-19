import { localization } from "@web/core/l10n/localization";
import { Component } from "@odoo/owl";

export class PriceFormatter extends Component {
    static template = "point_of_sale.PriceFormatter";
    static props = {
        price: { type: String },
    };

    get priceParts() {
        const trimmedPrice = this.props.price.trim();
        const prefixMatch = trimmedPrice.match(/^\D*/);
        const suffixMatch = trimmedPrice.match(/\D*$/);
        let isSuffix = false;
        let currencySymbol = prefixMatch ? prefixMatch[0].trim() : "";
        if (!currencySymbol) {
            currencySymbol = suffixMatch ? suffixMatch[0].trim() : "";
            isSuffix = true;
        }
        const numericPart = trimmedPrice.replace(currencySymbol, "").trim();
        const amountParts = numericPart.split(localization.decimalPoint);
        const decimal = amountParts[1] || "";
        const amountStr = amountParts[0] + (decimal ? localization.decimalPoint : ""); // ex. "1000."
        return {
            amountStr,
            decimal,
            currencySymbol,
            isSuffix,
        };
    }
}
