import { ServiceFactories } from "services";

declare module "registries" {
    interface GlobalRegistryCategories {
        "printer.type.handlers": (
            printer: Record<string, unknown>,
            duplex: boolean,
            jobs: Record<string, unknown>[],
            services: ServiceFactories
        ) => void | Promise<void>;
    }
}
