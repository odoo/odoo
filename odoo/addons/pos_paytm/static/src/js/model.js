/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentPaytm } from '@pos_paytm/js/payment_paytm';

    register_payment_method('paytm', PaymentPaytm);
