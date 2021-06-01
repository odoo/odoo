/** @odoo-module **/

import { browser } from "../core/browser/browser";
import AbstractStorageService from "web.AbstractStorageService";
import { ConnectionAbortedError, RPCError } from "../core/network/rpc_service";

export function mapDoActionOptionAPI(legacyOptions) {
    legacyOptions = Object.assign(legacyOptions || {});
    // use camelCase instead of snake_case for some keys
    Object.assign(legacyOptions, {
        additionalContext: legacyOptions.additional_context,
        clearBreadcrumbs: legacyOptions.clear_breadcrumbs,
        viewType: legacyOptions.view_type,
        resId: legacyOptions.res_id,
        onClose: legacyOptions.on_close,
    });
    delete legacyOptions.additional_context;
    delete legacyOptions.clear_breadcrumbs;
    delete legacyOptions.view_type;
    delete legacyOptions.res_id;
    delete legacyOptions.on_close;
    return legacyOptions;
}

export function makeLegacyActionManagerService(legacyEnv) {
    // add a service to redirect 'do-action' events triggered on the bus in the
    // legacy env to the action-manager service in the wowl env
    return {
        dependencies: ["action"],
        start(env) {
            function do_action(action, options) {
                const legacyOptions = mapDoActionOptionAPI(options);
                return env.services.action.doAction(action, legacyOptions);
            }
            legacyEnv.bus.on("do-action", null, (payload) => {
                const { action, options } = payload;
                do_action(action, options);
            });
            return { do_action };
        },
    };
}

export function makeLegacyRpcService(legacyEnv) {
    return {
        start(env) {
            legacyEnv.bus.on("rpc_request", null, (rpcId) => {
                env.bus.trigger("RPC:REQUEST", rpcId);
            });
            legacyEnv.bus.on("rpc_response", null, (rpcId) => {
                env.bus.trigger("RPC:RESPONSE", rpcId);
            });
            legacyEnv.bus.on("rpc_response_failed", null, (rpcId) => {
                env.bus.trigger("RPC:RESPONSE", rpcId);
            });
        },
    };
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
        dependencies: ["ui", "hotkey"],
        start(env) {
            const { ui, hotkey } = env.services;

            function getModalEl(dialog) {
                return dialog.modalRef ? dialog.modalRef.el : dialog.$modal[0];
            }

            function getCloseCallback(dialog) {
                return dialog.modalRef ? () => dialog._close() : () => dialog.$modal.modal("hide");
            }

            const tokensMap = new Map();

            function onOpenDialog(dialog) {
                ui.activateElement(getModalEl(dialog));
                const token = hotkey.registerHotkey("escape", getCloseCallback(dialog), {
                    altIsOptional: true,
                });
                tokensMap.set(token, dialog);
            }

            function onCloseDialog(dialog) {
                for (const [token, d] of tokensMap) {
                    if (d === dialog) {
                        ui.deactivateElement(getModalEl(dialog));
                        hotkey.unregisterHotkey(token);
                        tokensMap.delete(token);
                        break;
                    }
                }
            }

            legacyEnv.bus.on("legacy_dialog_opened", null, onOpenDialog);
            legacyEnv.bus.on("legacy_dialog_destroyed", null, onCloseDialog);

            legacyEnv.bus.on("owl_dialog_mounted", null, onOpenDialog);
            legacyEnv.bus.on("owl_dialog_willunmount", null, onCloseDialog);
        },
    };
}

export function makeLegacySessionService(legacyEnv, session) {
    return {
        dependencies: ["user"],
        start(env) {
            // userContext, Object.create is incompatible with legacy new Context
            function mapContext() {
                return Object.assign({}, env.services.user.context);
            }
            Object.defineProperty(legacyEnv.session, "userContext", {
                get: () => mapContext(),
            });
            Object.defineProperty(session, "user_context", {
                get: () => mapContext(),
            });
        },
    };
}

export function mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv) {
    // rpc
    legacyEnv.session.rpc = (...args) => {
        let rejection;
        const prom = new Promise((resolve, reject) => {
            const [route, params, settings = {}] = args;
            const jsonrpc = wowlEnv.services.rpc(route, params, { silent: settings.shadow });
            rejection = () => {
                jsonrpc.abort();
            };
            jsonrpc.then(resolve).catch((reason) => {
                if (reason instanceof RPCError) {
                    // we do not reject an error here because we want to pass through
                    // the legacy guardedCatch code
                    reject({ message: reason, event: $.Event(), legacy: true });
                } else if (reason instanceof ConnectionAbortedError) {
                    reject({ message: reason.name, event: $.Event("abort") });
                } else {
                    reject(reason);
                }
            });
        });
        prom.abort = rejection;
        return prom;
    };
    // Storages
    function mapStorage(storage) {
        const StorageService = AbstractStorageService.extend({ storage });
        return new StorageService();
    }

    legacyEnv.services.local_storage = mapStorage(browser.localStorage);
    legacyEnv.services.session_storage = mapStorage(browser.sessionStorage);
    // map WebClientReady
    wowlEnv.bus.on("WEB_CLIENT_READY", null, () => {
        legacyEnv.bus.trigger("web_client_ready");
    });

    legacyEnv.bus.on("clear_cache", null, () => {
        wowlEnv.bus.trigger("CLEAR-CACHES");
    });
}

export function breadcrumbsToLegacy(breadcrumbs) {
    if (!breadcrumbs) {
        return;
    }
    return breadcrumbs.slice().map((bc) => {
        return { title: bc.name, controllerID: bc.jsId };
    });
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
        start(env) {
            function notify({
                title,
                message,
                subtitle,
                buttons = [],
                sticky,
                type,
                className,
                onClose,
                messageIsHtml,
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

                return env.services.notification.create(message, {
                    sticky,
                    title,
                    type,
                    className,
                    onClose,
                    buttons,
                    messageIsHtml,
                });
            }

            function close(...args) {
                //the legacy close method had 3 arguments : the notification id, silent and wait.
                //the new close method only has 2 arguments : the notification id and wait.
                return env.services.notification.close(args[0], args[2] ? args[2] : 0);
            }

            legacyEnv.services.notification = { notify, close };
        },
    };
}
