/** @odoo-module **/

import { browser } from "../core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import {
    App,
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useComponent,
    useEnv,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import {
    ConnectionAbortedError,
    ConnectionLostError,
    RPCError,
} from "@web/core/network/rpc_service";

export const wowlServicesSymbol = Symbol("wowlServices");

/**
 * Deploys a service allowing legacy to add/remove commands.
 *
 * @param {object} legacyEnv
 * @returns a wowl deployable service
 */
export function mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv) {
    // store wowl services on the legacy env (used by the 'useWowlService' hook)
    legacyEnv[wowlServicesSymbol] = wowlEnv.services;
    Object.setPrototypeOf(legacyEnv.services, wowlEnv.services);
}

const reBSTooltip = /^bs-.*$/;

export function cleanDomFromBootstrap() {
    const body = document.body;
    // multiple bodies in tests
    // Bootstrap tooltips
    const tooltips = body.querySelectorAll("body .tooltip");
    for (const tt of tooltips) {
        if (Array.from(tt.classList).find((cls) => reBSTooltip.test(cls))) {
            tt.parentNode.removeChild(tt);
        }
    }
}

export function makeLegacyNotificationService(legacyEnv) {
    return {
        dependencies: ["notification"],
        start(env, { notification }) {
            let notifId = 0;
            const idsToRemoveFn = {};

            function notify({
                title,
                message,
                subtitle,
                buttons = [],
                sticky,
                type,
                className,
                onClose,
            }) {
                if (subtitle) {
                    title = [title, subtitle].filter(Boolean).join(" ");
                }
                if (!message && title) {
                    message = title;
                    title = undefined;
                }

                buttons = buttons.map((button) => {
                    return {
                        name: button.text,
                        icon: button.icon,
                        primary: button.primary,
                        onClick: button.click,
                    };
                });

                const removeFn = notification.add(message, {
                    sticky,
                    title,
                    type,
                    className,
                    onClose,
                    buttons,
                });
                const id = ++notifId;
                idsToRemoveFn[id] = removeFn;
                return id;
            }

            function close(id, _, wait) {
                //the legacy close method had 3 arguments : the notification id, silent and wait.
                //the new close method only has 2 arguments : the notification id and wait.
                const removeFn = idsToRemoveFn[id];
                delete idsToRemoveFn[id];
                if (wait) {
                    browser.setTimeout(() => {
                        removeFn(id);
                    }, wait);
                } else {
                    removeFn(id);
                }
            }

            legacyEnv.services.notification = { notify, close, add: notification.add };
        },
    };
}

export function makeLegacyRPC(wowlRPC) {
    return function rpc(route, args, options, target) {
        let rpcPromise = null;
        const promise = new Promise(function (resolve, reject) {
            rpcPromise = wowlRPC(route, args, options);
            rpcPromise
                .then(function (result) {
                    if (!target.isDestroyed()) {
                        resolve(result);
                    }
                })
                .catch(function (reason) {
                    if (!target.isDestroyed()) {
                        if (reason instanceof RPCError || reason instanceof ConnectionLostError) {
                            // we do not reject an error here because we want to pass through
                            // the legacy guardedCatch code
                            reject({ message: reason, event: $.Event(), legacy: true });
                        } else if (reason instanceof ConnectionAbortedError) {
                            reject({ message: reason.message, event: $.Event("abort") });
                        } else {
                            reject(reason);
                        }
                    }
                });
        });
        promise.abort = rpcPromise.abort.bind(rpcPromise);
        return promise;
    };
}

export function makeLegacyRPCService(legacyEnv) {
    return {
        dependencies: ["rpc"],
        start(_, { rpc: wowlRPC }) {
            const rpc = makeLegacyRPC(wowlRPC);
            legacyEnv.services.ajax = { rpc };
        },
    };
}

/**
 * This hook allows legacy owl Components to use services coming from the wowl env.
 * @param {string} serviceName
 * @returns {any}
 */
export function useWowlService(serviceName) {
    const component = useComponent();
    const env = component.env;
    component.env = { services: env[wowlServicesSymbol] };
    const service = useService(serviceName);
    component.env = env;
    return service;
}

export function createWidgetParent(env) {
    return {
        env,
        _trigger_up: (ev) => {
            if (ev.name === "call_service") {
                let args = ev.data.args || [];
                if (ev.data.service === "ajax" && ev.data.method === "rpc") {
                    // ajax service uses an extra 'target' argument for rpc
                    args = args.concat(ev.target);
                }
                const service = env.services[ev.data.service];
                const result = service[ev.data.method].apply(service, args);
                ev.data.callback(result);
            }
        },
    };
}

export function useWidget(refName, widgetClass, params = []) {
    const ref = useRef(refName);
    const env = useEnv();

    const parent = createWidgetParent(env);
    const widget = new widgetClass(parent, ...params);

    onWillStart(() => {
        return widget._widgetRenderAndInsert(() => {});
    });
    onMounted(() => {
        ref.el.append(widget.el);
    });
    onWillUnmount(() => {
        widget.destroy();
    });

    return widget;
}

const rootTemplate = xml`<SubComp t-props="state"/>`;
export async function attachComponent(parent, element, componentClass, props = {}) {
    class Root extends Component {
        static template = rootTemplate;
        static components = { SubComp: componentClass };
        state = useState(props);
    }

    const env = Component.env;
    const app = new App(Root, {
        env,
        templates,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });

    if (parent.__parentedMixin) {
        parent.__parentedChildren.push({
            get $el() {
                return $(app.root.el);
            },
            destroy() {
                app.destroy();
            },
        });
    }

    const component = await app.mount(element);
    const subComp = Object.values(component.__owl__.children)[0].component;
    return {
        component: subComp,
        destroy() {
            app.destroy();
        },
        update(props) {
            Object.assign(component.state, props);
        },
    };
}
