import { StoreLocator } from "./store_locator";
import { registry } from "@web/core/registry";

const StoreLocatorEdit = (I) =>
    class extends I {
        start() {
            super.start();
        }
    };

registry.category("public.interactions.edit").add("website.store_locator", {
    Interaction: StoreLocator,
    mixin: StoreLocatorEdit,
});
