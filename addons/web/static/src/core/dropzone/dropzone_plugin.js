import { computed, effect, Plugin, signal, untrack, useListener, usePlugin } from "@odoo/owl";
import { Dropzone } from "@web/core/dropzone/dropzone";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";
import { UIPlugin } from "@web/core/ui/ui_plugin";

/**
 * The dropzones of the files: while files are dragged over the page, each
 * element given to `add` is covered by a dropzone that receives them.
 */
export class DropzonePlugin extends Plugin {
    #overlay = usePlugin(OverlayPlugin);
    #ui = usePlugin(UIPlugin);
    #dragCount = signal(0);

    setup() {
        useListener(document, "dragenter", (ev) => this.#onDragEnter(ev), { capture: true });
        useListener(document, "dragleave", () => this.#onDragLeave(), { capture: true });
        // Prevents the browser to open the file when it is dropped outside of the dropzone.
        useListener(window, "dragover", (ev) => {
            if (this.#hasFiles(ev)) {
                ev.preventDefault();
            }
        });
        useListener(
            window,
            "drop",
            (ev) => {
                if (this.#hasFiles(ev)) {
                    ev.preventDefault();
                }
                this.#dragCount.set(0);
            },
            { capture: true }
        );
    }

    /**
     * Covers the element `ref()` with a dropzone while files are dragged, unless
     * it is behind a dialog or `isEnabled()` is false. E.g., in a setup:
     * `onWillDestroy(dropzone.add(this.rootRef, { onDrop: (files) => ... }))`
     *
     * @param {() => HTMLElement|null} ref
     * @param {Object} params
     * @param {(files: File[]) => void} params.onDrop
     * @param {string} [params.label] where the files go, shown in the dropzone
     * @param {string} [params.extraClass]
     * @param {() => boolean} [params.isEnabled]
     * @returns {() => void} removes the dropzone
     */
    add(ref, { isEnabled = () => true, ...props }) {
        const isShown = computed(() => {
            const el = this.#dragCount() > 0 && ref();
            return Boolean(el && this.#ui.activeElement().contains(el) && isEnabled());
        });
        return effect(() => {
            if (isShown()) {
                // the props are read now: a getter (e.g. `label`) gives its current value
                return untrack(() => this.#overlay.add(Dropzone, { ...props, ref }));
            }
        });
    }

    #hasFiles(ev) {
        return ev.dataTransfer?.types.includes("Files");
    }

    #onDragEnter(ev) {
        if (this.#dragCount() || this.#hasFiles(ev)) {
            this.#dragCount.set(this.#dragCount() + 1);
        }
    }

    #onDragLeave() {
        if (this.#dragCount()) {
            this.#dragCount.set(this.#dragCount() - 1);
        }
    }
}

services.add(DropzonePlugin);
