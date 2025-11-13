declare module "models" {
    import { DiscussApp as DiscussAppClass } from "@mail/core/public_web/discuss_app/discuss_app_model";

    export interface DiscussApp extends DiscussAppClass {}

    export interface Store {
        DiscussApp: StaticMailRecord<DiscussApp, typeof DiscussAppClass>;
    }

    export interface Models {
        DiscussApp: DiscussApp;
    }
}
