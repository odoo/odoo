/** @odoo-module **/

import { registry } from "../registry";
import { Dialog } from "./dialog";
import { DialogContainer } from "./dialog_container";

const { core } = owl;
const { EventBus } = core;

/**
 *  @typedef {{
 *      onClose?(): void;
 *  }} DialogServiceInterfaceAddOptions
 */
/**
 *  @typedef {{
 *      add(
 *          Component: any,
 *          props: {},
 *          options?: DialogServiceInterfaceAddOptions
 *      ): () => void;
 *  }} DialogServiceInterface
 */

export const dialogService = {
    /** @returns {DialogServiceInterface} */
    start() {
        const dialogs = {};
        const bus = new EventBus();
        let dialogId = 0;

        registry.category("main_components").add("DialogContainer", {
            Component: DialogContainer,
            props: { bus, dialogs },
        });

        function add(dialogClass, props, options = {}) {
            if (!(dialogClass.prototype instanceof Dialog)) {
                throw new Error(`${dialogClass.name} must be a subclass of Dialog`);
            }

            const id = ++dialogId;
            function close() {
                if (dialogs[id]) {
                    delete dialogs[id];
                    if (options.onClose) {
                        options.onClose();
                    }
                    bus.trigger("UPDATE");
                }
            }

            const dialog = {
                id,
                class: dialogClass,
                props: { ...props, close },
            };
            dialogs[id] = dialog;
            bus.trigger("UPDATE");

            return close;
        }

        return { add };
    },
};

registry.category("services").add("dialog", dialogService);
