/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentMollie } from "@pos_mollie/app/payment_mollie";

register_payment_method("mollie", PaymentMollie);
