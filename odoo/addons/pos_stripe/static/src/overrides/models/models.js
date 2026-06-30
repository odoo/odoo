/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";

register_payment_method("stripe", PaymentStripe);
