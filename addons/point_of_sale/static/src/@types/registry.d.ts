declare module "registries" {
    import { ScaleInterface } from "@point_of_sale/app/utils/scale/scale_interface";

    interface GlobalRegistryCategories {
        electronic_scales: typeof ScaleInterface;
    }
}
