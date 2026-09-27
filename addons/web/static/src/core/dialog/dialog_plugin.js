import { useSubEnv } from "@web/owl2/utils";
import {
    assertType,
    Component,
    markRaw,
    Plugin,
    proxy,
    t,
    useProps,
    usePlugin,
    xml,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";

class DialogWrapper extends Component {
    static template = xml`<t t-component="this.props.subComponent" t-props="this.props.subProps" />`;
    props = useProps({
        subComponent: t.any(),
        subProps: t.any(),
        subEnv: t.any(),
    });
    setup() {
        useSubEnv({ dialogData: this.props.subEnv });
    }
}

export const DialogOptionSchema = t.object({
    onClose: t.function().optional(),
    rootRef: t.or([t.signal(), t.function()]).optional(),
    scope: t.object().optional(),
});

export class DialogPlugin extends Plugin {
    /** @private */
    overlay = usePlugin(OverlayPlugin);
    /** @private */
    nextId = 0;
    /** @private */
    stack = [];

    /**
     * @param {typeof import("@odoo/owl").Component} dialogClass
     * @param {object} [props]
     * @param {DialogOptionSchema} [options]
     * @returns {() => Promise<void>}
     */
    add(dialogClass, props, options = {}) {
        assertType(options, DialogOptionSchema);
        const id = this.nextId++;
        const close = (params) => remove(params);
        const subEnv = proxy({
            id,
            close,
            isActive: true,
        });

        this.deactivate();
        this.stack.push(subEnv);
        document.body.classList.add("modal-open");
        let isBeingClosed = false;

        const scrollOrigin = { top: window.scrollY, left: window.scrollX };
        subEnv.scrollToOrigin = () => {
            if (!this.stack.length) {
                window.scrollTo(scrollOrigin);
            }
        };

        const remove = this.overlay.add(
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
                    this.stack.splice(
                        this.stack.findIndex((d) => d.id === id),
                        1
                    );
                    this.deactivate();
                    if (this.stack.length) {
                        this.stack.at(-1).isActive = true;
                    } else {
                        document.body.classList.remove("modal-open");
                    }
                },
                rootId: options.rootRef?.()?.getRootNode()?.host?.id,
                scope: options.scope,
            }
        );

        return remove;
    }

    closeAll(params) {
        for (const dialog of [...this.stack].reverse()) {
            dialog.close(params);
        }
    }

    /** @private */
    deactivate() {
        for (const subEnv of this.stack) {
            subEnv.isActive = false;
        }
    }
}

services.add(DialogPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the dialog service are removed
 * -----------------------------------------------------------------------------
 */
export const dialogService = {
    start() {
        return usePlugin(DialogPlugin);
    },
};

registry.category("services").add("dialog", dialogService);
