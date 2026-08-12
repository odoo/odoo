import { _t } from "@web/core/l10n/translation";

export function getPaymentMismatchErrorMessage(mismatch) {
    if (mismatch.currency_ask) {
        return _t(
            "Viva.com charged in %s, which does not match the currency set for this order (%s). The customer may have been charged; refund the transaction on the Viva terminal before retrying.",
            mismatch.currency_paid,
            mismatch.currency_ask
        );
    }
    if (mismatch.amount_ask) {
        return _t(
            "Viva.com charged %s, which does not match the total for this order (%s). The customer may have been charged; refund the transaction on the Viva terminal before retrying.",
            mismatch.amount_paid,
            mismatch.amount_ask
        );
    }
    return _t(
        "Viva.com payment could not be validated. The customer may have been charged; refund the transaction on the Viva terminal before retrying."
    );
}
