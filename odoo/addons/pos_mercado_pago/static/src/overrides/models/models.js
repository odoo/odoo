/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentMercadoPago } from "@pos_mercado_pago/app/payment_mercado_pago";

register_payment_method("mercado_pago", PaymentMercadoPago);
