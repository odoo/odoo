import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentRazorpay } from "@pos_razorpay/app/payment_razorpay";

register_payment_method("razorpay", PaymentRazorpay);
