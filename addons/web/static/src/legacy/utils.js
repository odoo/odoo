/** @odoo-module **/

import { App, Component, useState, xml } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

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

<<<<<<< HEAD
    if (parent.__parentedMixin) {
        parent.__parentedChildren.push({
            get $el() {
                return $(app.root.el);
            },
            destroy() {
                app.destroy();
            },
||||||| parent of 026f3fabbc80 (temp)
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

            legacyEnv.bus.on("set_legacy_command", null, setLegacyCommand);
            legacyEnv.bus.on("remove_legacy_command", null, removeLegacyCommand);
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
                    params.kwargs.context,
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
=======
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

            legacyEnv.bus.on("set_legacy_command", null, setLegacyCommand);
            legacyEnv.bus.on("remove_legacy_command", null, removeLegacyCommand);
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
            function setContext(update) {
                env.services.user.updateContext(update);
            }
            Object.defineProperty(legacyEnv.session, "userContext", {
                get: () => mapContext(),
                set: (update) => {
                    setContext(update);
                },
            });
            Object.defineProperty(session, "user_context", {
                get: () => mapContext(),
                set: (update) => {
                    setContext(update);
                },
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
            // Add user context in kwargs if there are kwargs
            if (params && params.kwargs) {
                params.kwargs.context = Object.assign(
                    {},
                    legacyEnv.session.user_context,
                    params.kwargs.context,
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
>>>>>>> 026f3fabbc80 (temp)
        });
    }

    const originalValidateTarget = App.validateTarget;
    App.validateTarget = () => {};
    const mountPromise = app.mount(element);
    App.validateTarget = originalValidateTarget;
    const component = await mountPromise;
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
