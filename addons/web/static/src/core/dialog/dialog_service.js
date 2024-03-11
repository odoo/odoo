/** @odoo-module **/

import { registry } from "../registry";
import { DialogContainer } from "./dialog_container";

import { markRaw, reactive } from "@odoo/owl";

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
    start(env) {
        const dialogs = reactive({});
        let dialogId = 0;

        registry.category("main_components").add("DialogContainer", {
            Component: DialogContainer,
            props: { dialogs },
        });

        function add(dialogClass, props, options = {}) {
            for (const dialog of Object.values(dialogs)) {
                dialog.dialogData.isActive = false;
            }
            const id = ++dialogId;
            function close() {
                if (dialogs[id]) {
                    delete dialogs[id];
                    Object.values(dialogs).forEach((dialog, i, dialogArr) => {
                        dialog.dialogData.isActive = i === dialogArr.length - 1;
                    });
                    if (options.onClose) {
                        options.onClose();
                    }
                }
            }

            const dialog = {
                id,
                class: dialogClass,
                props: markRaw({ ...props, close }),
                dialogData: {
                    isActive: true,
                    close,
                    id,
                },
            };
            const scrollOrigin = { top: window.scrollY, left: window.scrollX };
            dialog.dialogData.scrollToOrigin = () => {
                if (!Object.keys(dialogs).length) {
                    window.scrollTo(scrollOrigin);
                }
            };
            dialogs[id] = dialog;

            return close;
        }

        function closeAll() {
            for (const id in dialogs) {
                dialogs[id].dialogData.close();
            }
        }

        return { add, closeAll };
    },
};

registry.category("services").add("dialog", dialogService);
