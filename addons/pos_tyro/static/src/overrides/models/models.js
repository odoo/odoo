import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentTyro } from "@pos_tyro/app/payment_tyro";

register_payment_method("tyro", PaymentTyro);
