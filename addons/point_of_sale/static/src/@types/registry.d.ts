declare module "registries" {
    import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";

    interface GlobalRegistryCategories {
        pos_payment_providers: typeof PaymentInterface;
    }
}
