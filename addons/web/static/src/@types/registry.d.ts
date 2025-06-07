declare module "registries" {
    interface RegistryData<ItemShape, Categories> {
        __itemShape: ItemShape;
        __categories: Categories;
    }

    export interface GlobalRegistryCategories {}

    export type GlobalRegistry = RegistryData<null, GlobalRegistryCategories>;
}
