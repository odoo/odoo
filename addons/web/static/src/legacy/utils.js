/** @odoo-module **/

import { browser } from "../core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { Component, useComponent, xml } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import {
    ConnectionAbortedError,
    ConnectionLostError,
    RPCError,
} from "@web/core/network/rpc_service";

export const wowlServicesSymbol = Symbol("wowlServices");

class LegacyDialogContainer extends Component {
    static template = xml`<div class="o_dialog_container"/>`;
    static props = [];
}

/**
 * Returns a service that maps legacy dialogs
 * to new environment services behavior.
 *
 * @param {object} legacyEnv
 * @returns a wowl deployable service
 */
export function makeLegacyDialogMappingService(legacyEnv) {
    return {
        dependencies: ["ui", "hotkey", "overlay"],
        start(_, { ui, hotkey, overlay }) {
            overlay.add(LegacyDialogContainer, {});

            function getModalEl(dialog) {
                return dialog.modalRef ? dialog.modalRef.el : dialog.$modal[0];
            }

            function getCloseCallback(dialog) {
                return dialog.modalRef ? () => dialog._close() : () => dialog.$modal.modal("hide");
            }

            const dialogHotkeyRemoveMap = new Map();

            function onOpenDialog(dialog) {
                ui.activateElement(getModalEl(dialog));
                const remove = hotkey.add("escape", getCloseCallback(dialog));
                dialogHotkeyRemoveMap.set(dialog, remove);
            }

            function onCloseDialog(dialog) {
                ui.deactivateElement(getModalEl(dialog));
                if (dialogHotkeyRemoveMap.has(dialog)) {
                    const removeHotkey = dialogHotkeyRemoveMap.get(dialog);
                    removeHotkey();
                    dialogHotkeyRemoveMap.delete(dialog);
                }
            }

            legacyEnv.bus.on("legacy_dialog_opened", null, onOpenDialog);
            legacyEnv.bus.on("legacy_dialog_destroyed", null, onCloseDialog);
        },
    };
}

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

            legacyEnv.services.notification = { notify, close };
        },
    };
}

export function wrapSuccessOrFail(promise, { on_success, on_fail } = {}) {
    return promise.then(on_success || (() => {})).catch((reason) => {
        let alreadyThrown = false;
        if (on_fail) {
            alreadyThrown = on_fail(reason) === "alreadyThrown";
        }
        const error = reason instanceof Error && "cause" in reason ? reason.cause : reason;
        if (error instanceof Error && !alreadyThrown) {
            throw reason;
        }
    });
}

export function makeMomentLoaderService() {
    return {
        dependencies: ["localization"],
        async start(_, { localization }) {
            await loadJS(`/web/webclient/locale/${localization.code}`);
            const dow = (localization.weekStart || 0) % 7;
            moment.updateLocale(moment.locale(), {
                dow,
                doy: 7 + dow - 4, // Note: ISO 8601 week date: https://momentjscom.readthedocs.io/en/latest/moment/07-customization/16-dow-doy/
            });
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
            legacyEnv.services.rpc = rpc;
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
