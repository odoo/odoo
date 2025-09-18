// @ts-check

/** @module @web/ui/dialog/dialog_service - Service for programmatically opening, stacking, and closing modal dialogs */

import { Component, markRaw, reactive, useChildSubEnv, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
/** Internal wrapper that injects dialogData into the child environment. */
class DialogWrapper extends Component {
    static template = xml`<t t-component="props.subComponent" t-props="props.subProps" />`;
    static props = ["*"];
    setup() {
        useChildSubEnv({ dialogData: this.props.subEnv });
    }
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
 *      closeAll(params?: any): void;
 *  }} DialogServiceInterface
 */

/**
 * Service for programmatically opening modal dialogs.
 *
 * Manages a dialog stack, tracks active/inactive state, handles
 * `modal-open` CSS class on body, and scroll position restoration.
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
            const close = (params) => remove(params);
            const subEnv = reactive(
                /** @type {{ id: number, close: Function, isActive: boolean, scrollToOrigin?: () => void }} */ ({
                    id,
                    close,
                    isActive: true,
                }),
            );

            deactivate();
            stack.push(subEnv);
            document.body.classList.add("modal-open");
            let isBeingClosed = false;

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
                    onRemove: async (closeParams) => {
                        if (isBeingClosed) {
                            return;
                        }
                        isBeingClosed = true;
                        await options.onClose?.(closeParams);
                        const idx = stack.findIndex((d) => d.id === id);
                        if (idx !== -1) {
                            stack.splice(idx, 1);
                        }
                        deactivate();
                        if (stack.length) {
                            stack.at(-1).isActive = true;
                        } else {
                            document.body.classList.remove("modal-open");
                        }
                    },
                    rootId: options.context?.root?.el?.getRootNode()?.host?.id,
                },
            );

            return remove;
        };

        function closeAll(params) {
            for (const dialog of stack.toReversed()) {
                dialog.close(params);
            }
        }

        return { add, closeAll };
    },
};

registry.category("services").add("dialog", dialogService);
