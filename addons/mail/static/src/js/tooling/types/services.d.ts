/* add this file in jsconfig.json, in typeRoots array */
declare module "services" {
    import { storeService } from "@mail/core/common/store_plugin";

    export interface Services {
        "mail.store": typeof storeService;
    }
}
