import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentPinelabs } from "@pos_pinelabs/app/utils/payment_pinelabs";

register_payment_method("pinelabs", PaymentPinelabs);
