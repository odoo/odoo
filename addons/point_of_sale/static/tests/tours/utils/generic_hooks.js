export class GenericHooks {
    static onProductScreen() {
        // This function should be overridden in the localization
        return [];
    }

    static afterValidateHook() {
        // This function can be overridden in the localization to add steps after payment validation
        return [];
    }
}
