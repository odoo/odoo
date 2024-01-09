/** @odoo-module */

import { Plugin } from "../plugin";
import { getCurrentRect } from "./utils";

/**
 * Provide the following feature:
 * - adding a component in overlay above the editor, with proper positioning
 */
export class OverlayPlugin extends Plugin {
    static name = "overlay";
    static shared = ["createOverlay"];

    setup() {
        this.overlays = [];
        this.addDomListener(document, "scroll", this.onScroll, true);
        this.addDomListener(window, "resize", this.updatePositions, true);
    }

    destroy() {
        for (const overlay of this.overlays) {
            overlay.close();
        }
    }

    createOverlay(Component, position, props) {
        const overlay = new Overlay(this, Component, position, props);
        this.overlays.push(overlay);
        return overlay;
    }

    onScroll(ev) {
        if (ev.target.contains(this.el)) {
            this.updatePositions();
        }
    }

    updatePositions() {
        for (const overlay of this.overlays) {
            overlay.updatePosition();
        }
    }
}

export class Overlay {
    constructor(plugin, C, position, props) {
        this.plugin = plugin;
        this.el = null;
        this.isOpen = false;
        this.C = C;
        this.position = position;
        this.props = props;
        this._remove = null;
    }
    open() {
        if (this.isOpen) {
            this.updatePosition();
        } else {
            this.isOpen = true;
            this._remove = this.plugin.services.overlay.add(this.C, {
                close: () => this.close(),
                onMounted: (el) => {
                    this.el = el;
                    this.updatePosition();
                },
                ...this.props,
            });
        }
    }
    close() {
        this.isOpen = false;
        if (this._remove) {
            this._remove();
            this.el = null;
        }
    }
    updatePosition() {
        if (!this.el) {
            return;
        }
        const elRect = this.plugin.el.getBoundingClientRect();
        const overlayRect = this.el.getBoundingClientRect();
        const Y_OFFSET = 6;

        // autoclose if overlay target is out of view
        const rect = getCurrentRect();
        if (rect.bottom < elRect.top - 10 || rect.top > elRect.bottom + Y_OFFSET) {
            // position below
            this.close();
            return;
        }

        let top;
        if (this.position === "top") {
            // try position === 'top'
            top = rect.top - Y_OFFSET - overlayRect.height;
            // fallback on position === 'bottom'
            if (top < elRect.top) {
                top = rect.bottom + Y_OFFSET;
            }
        } else {
            // try position === "bottom"
            top = rect.bottom + Y_OFFSET;
            if (top > elRect.bottom) {
                top = rect.top - Y_OFFSET - overlayRect.height;
            }
        }
        const left = rect.left;
        this.el.style.left = left + "px";
        this.el.style.top = top + "px";
    }
}
