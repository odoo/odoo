declare module "registries" {
    import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
    import { ScaleInterface } from "@point_of_sale/app/services/scale_interface";

    interface GlobalRegistryCategories {
        electronic_payment_interfaces: typeof PaymentInterface;
        electronic_scales: typeof ScaleInterface;
    }
}
