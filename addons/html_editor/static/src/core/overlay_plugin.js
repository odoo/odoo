import { markRaw, EventBus } from "@odoo/owl";
import { Plugin } from "../plugin";
import { EditorOverlay } from "./overlay";

/**
 * @typedef { Object } OverlayShared
 * @property { OverlayPlugin['createOverlay'] } createOverlay
 */

/**
 * Provides the following feature:
 * - adding a component in overlay above the editor, with proper positioning
 */
export class OverlayPlugin extends Plugin {
    static id = "overlay";
    static dependencies = ["history", "selection"];
    static shared = ["createOverlay"];

    overlays = [];

    destroy() {
        super.destroy();
        for (const overlay of this.overlays) {
            overlay.close();
        }
    }

    /**
     * Creates an overlay component and adds it to the list of overlays.
     *
     * @param {Function} Component
     * @param {Object} [props={}]
     * @param {Object} [options]
     * @returns {Overlay}
     */
    createOverlay(Component, props = {}, options) {
        const overlay = new Overlay(this, Component, props, options);
        this.overlays.push(overlay);
        return overlay;
    }
}

export class Overlay {
    constructor(plugin, C, props, options) {
        this.plugin = plugin;
        this.C = C;
        this.editorOverlayProps = props;
        this.options = options;
        this.isOpen = false;
        this._remove = null;
        this.component = null;
        this.bus = new EventBus();
    }

    /**
     * @param {Object} options
     * @param {HTMLElement | null} [options.target] for the overlay.
     *  If null or undefined, the current selection will be used instead
     * @param {any} [options.props] overlay component props
     */
    open({ target, props }) {
        if (this.isOpen) {
            this.updatePosition();
        } else {
            this.isOpen = true;
            const selection = this.plugin.editable.ownerDocument.getSelection();
            let initialSelection;
            if (selection && selection.type !== "None") {
                initialSelection = {
                    range: selection.getRangeAt(0),
                };
            }
            this._remove = this.plugin.services.overlay.add(
                EditorOverlay,
                markRaw({
                    ...this.editorOverlayProps,
                    Component: this.C,
                    editable: this.plugin.editable,
                    props,
                    target,
                    initialSelection,
                    bus: this.bus,
                    close: this.close.bind(this),
                    isOverlayOpen: this.isOverlayOpen.bind(this),
                    shared: {
                        ignoreDOMMutations: this.plugin.dependencies.history.ignoreDOMMutations,
                        getSelectionData: this.plugin.dependencies.selection.getSelectionData,
                    },
                }),
                {
                    ...this.options,
                }
            );
        }
    }

    close() {
        this.isOpen = false;
        if (this._remove) {
            this._remove();
        }
    }

    isOverlayOpen() {
        return this.isOpen;
    }

    updatePosition() {
        this.bus.trigger("updatePosition");
    }
}
