import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentSix } from "@pos_iot_six/js/payment_six";

register_payment_method("six_iot", PaymentSix);
