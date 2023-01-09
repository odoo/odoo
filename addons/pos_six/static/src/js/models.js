/** @odoo-module */

import { register_payment_method } from "@point_of_sale/js/models";
import PaymentSix from "@pos_six/js/payment_six";

register_payment_method("six", PaymentSix);
