declare module "models" {
    import { ProductCatalogRecord as ProductCatalogRecordClass } from "@product/product_catalog/kanban_model";

    export interface ProductCatalogRecord extends ProductCatalogRecordClass {}
    export interface Store {
        ProductCatalogRecord: ProductCatalogRecord;
    }

    export interface Models {
        ProductCatalogRecord: ProductCatalogRecord;
    }
}
