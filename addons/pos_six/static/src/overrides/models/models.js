import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { PaymentSix } from "@pos_six/app/payment_six";

register_payment_method("six", PaymentSix);
