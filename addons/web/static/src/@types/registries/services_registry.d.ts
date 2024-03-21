declare module "registries" {
    import { Services } from "services";

    export interface ServicesRegistryItemShape<T = any> {
        async?: boolean | string[];
        dependencies?: (keyof Services)[];
        start(env: object, dependencies: Services): T;
    }

    interface GlobalRegistryCategories {
        services: ServicesRegistryItemShape;
    }
}
