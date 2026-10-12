declare module "services" {
    import { translationModeServiceFactory } from "../translation_mode_service";

    export interface Services {
        translation_mode: typeof translationModeServiceFactory;
    }
}
