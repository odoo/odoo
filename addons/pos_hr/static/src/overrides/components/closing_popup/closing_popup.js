import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { PaymentMethodBreakdown } from "./payment_method_breakdown/payment_method_breakdown";
import { AccordionItem } from "@pos_hr/app/generic_components/accordion_item/accordion_item";

patch(ClosePosPopup, {
    components: { ...ClosePosPopup.components, PaymentMethodBreakdown, AccordionItem },
});
