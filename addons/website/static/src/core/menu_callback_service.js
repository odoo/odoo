import { registry } from "@web/core/registry";

registry.category("services").add("menu_callback", {
    start() {
        const updateCallbacks = new Set();
        return {
            updateCallbacks,
            registerCallback(fn) {
                updateCallbacks.add(fn);
                return () => updateCallbacks.delete(fn)
            },
        }
    }
});
