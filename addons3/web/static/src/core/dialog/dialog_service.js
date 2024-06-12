/** @odoo-module **/

import { registry } from "../registry";
import { Component, markRaw, reactive, xml } from "@odoo/owl";
import { WithEnv } from "../utils/components";

class DialogWrapper extends Component {
    static template = xml`
        <WithEnv env="{ dialogData: props.subEnv }">
            <t t-component="props.subComponent" t-props="props.subProps" />
        </WithEnv>
    `;
    static components = { WithEnv };
    static props = ["*"];
}

/**
 *  @typedef {{
 *      onClose?(): void;
 *  }} DialogServiceInterfaceAddOptions
 */
/**
 *  @typedef {{
 *      add(
 *          Component: typeof import("@odoo/owl").Component,
 *          props: {},
 *          options?: DialogServiceInterfaceAddOptions
 *      ): () => void;
 *  }} DialogServiceInterface
 */

export const dialogService = {
    dependencies: ["overlay"],
    /** @returns {DialogServiceInterface} */
    start(env, { overlay }) {
        const stack = [];
        let nextId = 0;

        const deactivate = () => {
            for (const subEnv of stack) {
                subEnv.isActive = false;
            }
        };

        const add = (dialogClass, props, options = {}) => {
            const id = nextId++;
            const close = () => remove();
            const subEnv = reactive({
                id,
                close,
                isActive: true,
            });

            deactivate();
            stack.push(subEnv);
            document.body.classList.add("modal-open");

            const scrollOrigin = { top: window.scrollY, left: window.scrollX };
            subEnv.scrollToOrigin = () => {
                if (!stack.length) {
                    window.scrollTo(scrollOrigin);
                }
            };

            const remove = overlay.add(
                DialogWrapper,
                {
                    subComponent: dialogClass,
                    subProps: markRaw({ ...props, close }),
                    subEnv,
                },
                {
                    onRemove: () => {
                        stack.pop();
                        deactivate();
                        if (stack.length) {
                            stack.at(-1).isActive = true;
                        } else {
                            document.body.classList.remove("modal-open");
                        }
                        options.onClose?.();
                    },
                }
            );

            return remove;
        };

        function closeAll() {
            for (const dialog of [...stack].reverse()) {
                dialog.close();
            }
        }

        return { add, closeAll };
    },
};

registry.category("services").add("dialog", dialogService);
