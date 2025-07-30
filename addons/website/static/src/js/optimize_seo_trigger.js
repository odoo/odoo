/** @odoo-module **/

import { Component, onMounted, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { OptimizeSEODialog } from "@website/components/dialog/seo";

class SEOTrigger extends Component {
    static template = xml`<div/>`;

    setup() {
        const dialog = useService("dialog");
        const website = useService("website");

        onMounted(async () => {
            const mainParams = new URLSearchParams(window.location.search);
            const rawPath = mainParams.get("path");

            if (!rawPath) return;

            const nestedParams = new URLSearchParams(
                rawPath.split("?")[1] || ""
            );
            if (!nestedParams.has("seo_optimize")) return;

            try {
                await this._waitUntil(
                    () => {
                        return !!website.currentWebsite?.metadata?.mainObject;
                    },
                    { interval: 300, timeout: 10000 }
                );
            } catch {
                console.warn("SEOTrigger: Metadata not ready in time.");
                return;
            }

            const meta = website.currentWebsite.metadata;
            const { id: resId, model: resModel } = meta.mainObject || {};
            const path = meta.path;

            if (!resId || !resModel) return;

            dialog.add(OptimizeSEODialog, {
                currentWebsite: {
                    id: website.currentWebsite.id,
                    metadata: {
                        mainObject: { id: resId, model: resModel },
                        path,
                    },
                },
            });
        });
    }

    async _waitUntil(conditionFn, { interval = 300, timeout = 10000 } = {}) {
        const start = Date.now();
        return new Promise((resolve, reject) => {
            const check = () => {
                if (conditionFn()) return resolve(true);
                if (Date.now() - start >= timeout)
                    return reject(new Error("Timeout"));
                setTimeout(check, interval);
            };
            check();
        });
    }
}

registry.category("main_components").add("seo_trigger", {
    Component: SEOTrigger,
});
