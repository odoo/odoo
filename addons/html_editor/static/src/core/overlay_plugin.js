import { markRaw, EventBus } from "@odoo/owl";
import { Plugin } from "../plugin";
import { EditorOverlay } from "./overlay";
import { throttleForAnimation } from "@web/core/utils/timing";
import { findUpTo } from "@html_editor/utils/dom_traversal";

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
    static dependencies = ["history"];
    static shared = ["createOverlay"];
    resources = {
        step_added_handlers: this.getScrollContainer.bind(this),
    };

    overlays = [];

    setup() {
        this.iframe = this.window.frameElement;
        this.topDocument = this.iframe?.ownerDocument || this.document;
        this.container = this.getScrollContainer();
        this.throttledUpdateContainer = throttleForAnimation(() => {
            this.container = this.getScrollContainer();
        });
        this.addDomListener(this.topDocument.defaultView, "resize", this.throttledUpdateContainer);
    }

    destroy() {
        this.throttledUpdateContainer.cancel();
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
        const overlay = new Overlay(this, Component, () => this.container, props, options);
        this.overlays.push(overlay);
        return overlay;
    }

    getScrollContainer() {
        const isScrollable = (element) =>
            element.scrollHeight > element.clientHeight &&
            ["auto", "scroll"].includes(getComputedStyle(element).overflowY);

        return (
            findUpTo(this.iframe || this.editable, null, isScrollable) ||
            this.topDocument.documentElement
        );
    }
}

export class Overlay {
    constructor(plugin, C, getContainer, props, options) {
        this.plugin = plugin;
        this.C = C;
        this.editorOverlayProps = props;
        this.options = options;
        this.isOpen = false;
        this._remove = null;
        this.component = null;
        this.bus = new EventBus();
        this.getContainer = getContainer;
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
                    getContainer: this.getContainer,
                    close: this.close.bind(this),
                    isOverlayOpen: this.isOverlayOpen.bind(this),
                    history: {
                        ignoreDOMMutations: this.plugin.dependencies.history.ignoreDOMMutations,
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

    /**
     * Check whether `el` is in the overlay or another overlay on top
     *
     * @param {HTMLElement} el
     * @returns {boolean}
     */
    overlayContainsElement(el) {
        const query = { el };
        this.bus.trigger("queryOverlayContainsElement", query);
        return query.isContained;
    }
}
