import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentMethodBreakdown } from "./payment_method_breakdown/payment_method_breakdown";
import { AccordionItem } from "@point_of_sale/app/generic_components/accordion_item/accordion_item";

patch(ClosePosPopup, {
    components: { ...ClosePosPopup.components, PaymentMethodBreakdown, AccordionItem },
    get paymentMethodBreakdownTitle() {
        return _t("Payments in %(paymentMethod)s", {
            paymentMethod: this.props.default_cash_details.name,
        });
    },
});
