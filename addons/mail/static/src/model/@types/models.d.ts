declare module "models" {
    import { Store as StoreClass } from "@mail/model/store";

    export interface Store extends StoreClass {}

    type StaticMailRecord<ClassInterface, JSClassType> = Omit<JSClassType, "get" | "insert" | "records"> & {
        get: (data: any) => ClassInterface;
        insert: <D extends object | object[]>(data: D, options?: object) => D extends object[] ? ClassInterface[] : ClassInterface;
        records: { [localId: string]: ClassInterface };
    };

    export interface Models {
        Store: Store;
    }
}
