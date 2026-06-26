import { App, EventBus } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";
import { appTranslateFn } from "@web/core/l10n/translation";
import { services } from "@web/core/services";
import { getTemplate } from "@web/core/templates";
import { session } from "@web/session";

/**
 * @typedef {{
 *  bus: EventBus;
 *  debug: string;
 *  services: import("services").ServiceFactories;
 *  readonly isSmall: boolean;
 * }} OdooEnv
 */

/**
 * Return a value Odoo Env object
 *
 * @returns {OdooEnv}
 */
export function makeEnv() {
    const bus = new EventBus();
    return {
        bus,
        services: {},
        debug: odoo.debug,
        get isSmall() {
            throw new Error("UI service not initialized!");
        },
    };
}

export const customDirectives = {
    // t-custom-click="handler"
    // This custom directive will add two even listeners ("click"; "auxclick") and call the global value "click".
    // The global value "click" will call the handler with two parameters :
    //      - ev (the original event)
    //      - isMiddleClick (a boolean that says if the user middle clicked, or if he did a ctrl+click)
    //
    click: (node, value, modifiers) => {
        let mods = "";
        if (modifiers.includes("synthetic")) {
            mods += ".synthetic";
        }
        if (modifiers.includes("capture")) {
            mods += ".capture";
        }
        const handlerFunction = `(ev) => __globals__.click(ev, (${value}).bind(this), '${JSON.stringify(
            modifiers
        )}')`;
        node.setAttribute(`t-on-click${mods}`, handlerFunction);
        node.setAttribute(`t-on-auxclick${mods}`, handlerFunction);
    },
};

export const globalValues = {
    click: (ev, value, modifiers) => {
        if (ev.button === 0 || ev.button === 1) {
            modifiers = JSON.parse(modifiers);
            for (const modifier of modifiers) {
                if (modifier === "stop") {
                    ev.stopPropagation();
                }
                if (modifier === "prevent") {
                    ev.preventDefault();
                }
            }
            const ctrlKey = isMacOS() ? ev.metaKey : ev.ctrlKey;
            const isMiddleClick = (ctrlKey && ev.button === 0) || ev.button === 1;
            value(ev, isMiddleClick);
        }
    },
};

/**
 * Create an application with a given component as root and mount it. If no env
 * is provided, the application will be treated as a "root": an env will be
 * created and the services will be started, it will also be set as the root
 * in `__WOWL_DEBUG__`
 *
 * @param {import("@odoo/owl").Component} component the component to mount
 * @param {HTMLElement} target the HTML element in which to mount the app
 * @param {Partial<ConstructorParameters<typeof App>[1]>} [appConfig] object
 *  containing a (partial) config for the app.
 */
export async function mountComponent(component, target, appConfig = {}) {
    const env = makeEnv();
    const app = new App({
        customDirectives,
        dev: env.debug || session.test_mode,
        env,
        getTemplate,
        globalValues,
        name: appConfig.name || component.constructor.name,
        plugins: services,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
        ...appConfig,
    });
    await app.pluginManager.ready;
    const root = await app.createRoot(component, { ...appConfig }).mount(target);
    odoo.__WOWL_DEBUG__ = { root };
    return { env, app, root };
}
