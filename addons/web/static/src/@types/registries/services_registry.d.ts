declare module "registries" {
    import { Services } from "services";

    export interface ServicesRegistryItemShape<T = any> {
        async?: boolean | string[];
        dependencies?: string[];
        start(env: any, dependencies: any): T;
    }

    interface GlobalRegistryCategories {
        services: ServicesRegistryItemShape;
    }
}
