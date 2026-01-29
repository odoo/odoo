/** @odoo-module */

import { App } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

class ComponentManager {
    constructor(env) {
        this.env = env;
        this.appConfig = {
            templates,
            env: env,
            dev: env.debug,
            translateFn: _t,
            translatableAttributes: ["data-tooltip"],
        };
        /** @type {Map<HTMLElement, { app: App, mountProm: Promise<any> }>} */
        this.apps = new Map();
    }
    async mountComponents() {
        for (const [key, component] of registry.category("public_components").getEntries()) {
            for (const el of document.querySelectorAll(
                `owl-component[name="${CSS.escape(key)}"]`
            )) {
                if (!this.apps.has(el)) {
                    const props = JSON.parse(el.getAttribute("props") || "{}");

                    const app = new App(component, {
                        ...this.appConfig,
                        props,
                    });
                    this.apps.set(el, { app, mountProm: app.mount(el) });
                }
            }
        }
        await Promise.all([...this.apps.values()].map(({ mountProm }) => mountProm));
    }
    destroyComponents() {
        for (const { app } of this.apps.values()) {
            app.destroy();
        }
        this.apps.clear();
    }
}

export const publicComponentService = {
    start(env) {
        return new ComponentManager(env);
    },
};

registry.category("services").add("public_component", publicComponentService);
