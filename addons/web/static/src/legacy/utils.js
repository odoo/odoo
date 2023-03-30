/** @odoo-module **/

import { browser } from "../core/browser/browser";
import AbstractStorageService from "web.AbstractStorageService";
import {
    ConnectionAbortedError,
    RPCError,
    makeErrorFromResponse,
    ConnectionLostError,
} from "../core/network/rpc_service";
import { ErrorDialog } from "../core/errors/error_dialogs";
import { useService } from "@web/core/utils/hooks";

import { Component, useComponent, xml } from "@odoo/owl";

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

            legacyEnv.bus.on("owl_dialog_mounted", null, onOpenDialog);
            legacyEnv.bus.on("owl_dialog_willunmount", null, onCloseDialog);
        },
    };
}

/**
 * Deploys a service allowing legacy to add/remove commands.
 *
 * @param {object} legacyEnv
 * @returns a wowl deployable service
 */
export function makeLegacyCommandService(legacyEnv) {
    return {
        dependencies: ["command"],
        start(env) {
            const { command } = env.services;

            const commandRemoveMap = new Map();

            function setLegacyCommand(uniqueId, getCommandDefinition) {
                const { name, action, options } = getCommandDefinition(env);
                removeLegacyCommand(uniqueId);
                commandRemoveMap.set(uniqueId, command.add(name, action, options));
            }

            function removeLegacyCommand(uniqueId) {
                if (commandRemoveMap.has(uniqueId)) {
                    const removeCommand = commandRemoveMap.get(uniqueId);
                    removeCommand();
                    commandRemoveMap.delete(uniqueId);
                }
            }
            function openMainPalette(config = {}) {
                command.openMainPalette(config);
            }

            legacyEnv.bus.on("set_legacy_command", null, setLegacyCommand);
            legacyEnv.bus.on("remove_legacy_command", null, removeLegacyCommand);
            legacyEnv.bus.on("openMainPalette", null, openMainPalette);
        },
    };
}

export function makeLegacyDropdownService(legacyEnv) {
    return {
        dependencies: ["ui", "hotkey"],
        start(_, { ui, hotkey }) {
            legacyEnv.services.ui = ui;
            legacyEnv.services.hotkey = hotkey;
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
    // store wowl services on the legacy env (used by the 'useWowlService' hook)
    legacyEnv[wowlServicesSymbol] = wowlEnv.services;

    // rpc
    legacyEnv.session.rpc = (...args) => {
        let rejection;
        const prom = new Promise((resolve, reject) => {
            const [route, params, settings = {}] = args;
            // Add user context in kwargs if there are kwargs
            if (params && params.kwargs) {
                params.kwargs.context = Object.assign(
                    {},
                    legacyEnv.session.user_context,
                    params.kwargs.context
                );
            }
            const jsonrpc = wowlEnv.services.rpc(route, params, {
                silent: settings.shadow,
                xhr: settings.xhr,
            });
            rejection = () => {
                jsonrpc.abort();
            };
            jsonrpc.then(resolve).catch((reason) => {
                if (reason instanceof RPCError || reason instanceof ConnectionLostError) {
                    // we do not reject an error here because we want to pass through
                    // the legacy guardedCatch code
                    reject({ message: reason, event: $.Event(), legacy: true });
                } else if (reason instanceof ConnectionAbortedError) {
                    reject({ message: reason.message, event: $.Event("abort") });
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
    legacyEnv.services.dialog = wowlEnv.services.dialog;
    // map WebClientReady
    wowlEnv.bus.addEventListener("WEB_CLIENT_READY", () => {
        legacyEnv.bus.trigger("web_client_ready");
    });

    wowlEnv.bus.addEventListener("SCROLLER:ANCHOR_LINK_CLICKED", (ev) => {
        legacyEnv.bus.trigger("SCROLLER:ANCHOR_LINK_CLICKED", ev.detail);
    });

    legacyEnv.bus.on("clear_cache", null, () => {
        wowlEnv.bus.trigger("CLEAR-CACHES");
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

export function makeLegacyCrashManagerService(legacyEnv) {
    return {
        dependencies: ["dialog"],
        start(env) {
            legacyEnv.services.crash_manager = {
                show_message(message) {
                    env.services.dialog.add(ErrorDialog, { traceback: message });
                },
                rpc_error(errorResponse) {
                    // Will be handled by error_service
                    Promise.reject(makeErrorFromResponse(errorResponse));
                },
            };
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

export function makeLegacyRainbowManService(legacyEnv) {
    return {
        dependencies: ["effect"],
        start(env, { effect }) {
            legacyEnv.bus.on("show-effect", null, (payload) => {
                effect.add(payload);
            });
        },
    };
}

export function useLegacyRefs() {
    const env = owl.useEnv();

    let legacyRefs;
    if (env.legacyRefs) {
        legacyRefs = env.legacyRefs;
    } else {
        legacyRefs = {
            component: null,
            widget: null,
        };
    }

    owl.useChildSubEnv({
        legacyRefs,
    });

    return legacyRefs;
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
