import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

patch(router, {
    pushState: () => {},
    replaceState: () => {},
    cancelPushes: () => {},
    addLockedKey: () => {},
});
