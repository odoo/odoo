import { registry } from "@web/core/registry";

export const iframeService = {
    start() {
        const iframe = document.createElement("iframe");
        const readyPromise = new Promise((resolve) => (iframe.onload = resolve));

        document.body.appendChild(iframe);

        return {
            async append(...elements) {
                await readyPromise;

                iframe.contentDocument?.append(...elements);
            },
        };
    },
};

registry.category("services").add("iframe", iframeService);
