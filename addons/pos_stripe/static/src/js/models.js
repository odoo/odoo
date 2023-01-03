/** @odoo-module */
import { register_payment_method } from "@point_of_sale/js/models";
import PaymentStripe from "@pos_stripe/js/payment_stripe";

register_payment_method("stripe", PaymentStripe);
