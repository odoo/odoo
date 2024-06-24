import { markRaw, EventBus } from "@odoo/owl";
import { Plugin } from "../plugin";
import { EditorOverlay } from "./overlay";

/**
 * Provide the following feature:
 * - adding a component in overlay above the editor, with proper positioning
 */
export class OverlayPlugin extends Plugin {
    static name = "overlay";
    static shared = ["createOverlay"];

    overlays = [];

    destroy() {
        super.destroy();
        for (const overlay of this.overlays) {
            overlay.close();
        }
    }

    createOverlay(Component, config) {
        const overlay = new Overlay(this, Component, config);
        this.overlays.push(overlay);
        return overlay;
    }
}

export class Overlay {
    constructor(plugin, C, config) {
        this.plugin = plugin;
        this.C = C;
        this.config = config;
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
            this._remove = this.plugin.services.overlay.add(
                EditorOverlay,
                markRaw({
                    config: this.config,
                    Component: this.C,
                    editable: this.plugin.editable,
                    props,
                    target,
                    bus: this.bus,
                }),
                {
                    sequence: this.config.sequence || 50,
                }
            );
        }
    }

    close() {
        this.isOpen = false;
        if (this._remove) {
            this._remove();
        }
        this.config.onClose?.();
    }

    updatePosition() {
        this.bus.trigger("updatePosition");
    }
}
