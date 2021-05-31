/** @odoo-module **/

import { registry } from "../registry";
import { Dialog } from "./dialog";

const { core } = owl;
const { EventBus } = core;

export const dialogService = {
    start() {
        const bus = new EventBus();
        let dialogId = 0;
        function open(dialogClass, props, options) {
            if (!(dialogClass.prototype instanceof Dialog)) {
                throw new Error(dialogClass.name + " must be a subclass of Dialog");
            }
            const id = ++dialogId;
            const dialog = {
                id,
                class: dialogClass,
                props,
                options,
            };
            bus.trigger("ADD", dialog);
            return id;
        }
        function close(id) {
            bus.trigger("CLOSE", id);
        }
        return { open, close, bus };
    },
};

registry.category("services").add("dialog", dialogService);
