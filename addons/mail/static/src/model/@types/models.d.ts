declare module "models" {
    import { Store as StoreClass } from "@mail/model/store";

    export interface Store extends StoreClass {}
    export interface Store {
        Store: Store;
    }

    export interface Models {
        Store: Store;
    }
}
