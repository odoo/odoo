/** @odoo-module */

import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentSix } from "@pos_six/app/payment_six";

register_payment_method("six", PaymentSix);
