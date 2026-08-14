/** @odoo-module */

import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { _t } from "@web/core/l10n/translation";

/**
 * ConfirmPopup escapes its body, which would print the link to the faulty invoice as raw
 * markup. This popup renders it.
 */
export class ZatcaErrorPopup extends ConfirmPopup {
    static template = "l10n_sa_edi_pos.ZatcaErrorPopup";
    static defaultProps = {
        ...ConfirmPopup.defaultProps,
        title: _t("ZATCA Validation Error"),
    };
}
