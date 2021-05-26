/** @odoo-module **/

import { useService } from "../service_hook";

const { onWillUnmount, useComponent } = owl.hooks;

export function usePopover() {
    const keys = new Set();
    const service = useService("popover");
    const component = useComponent();

    onWillUnmount(function () {
        for (const key of keys) {
            service.remove(key);
        }
        keys.clear();
    });
    return Object.assign(Object.create(service), {
        add(params) {
            const newParams = Object.create(params);
            newParams.onClose = function (key) {
                if (!params.keepOnClose) {
                    // manager will delete the popover if keepOnClose is falsy
                    keys.delete(key);
                }
                if (params.onClose && component.__owl__.status !== 5 /* DESTROYED */) {
                    params.onClose(key);
                }
            };
            const key = service.add(newParams);
            keys.add(key);
            return key;
        },
        remove(key) {
            keys.delete(key);
            service.remove(key);
        },
    });
}
