import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import { PaymentVivaWallet } from "@pos_viva_wallet/app/payment_viva_wallet";

register_payment_method("viva_wallet", PaymentVivaWallet);
