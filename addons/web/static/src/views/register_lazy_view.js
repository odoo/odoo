import { registry } from "@web/core/registry";

export function registerLazyView(key, view) {
    const viewInfo = registry.category("views").get(key);
    Object.setPrototypeOf(viewInfo, view);
    return view;
}
