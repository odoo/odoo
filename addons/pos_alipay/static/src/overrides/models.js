/** @odoo-module */

import { PaymentAlipay } from "@pos_alipay/app/payment_alipay";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";

register_payment_method("alipay", PaymentAlipay);
