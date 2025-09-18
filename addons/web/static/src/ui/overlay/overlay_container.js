// @ts-check

/** @module @web/ui/overlay/overlay_container - Renders overlay entries (popovers, dialogs, effects) with nested click-away tracking */

import {
    Component,
    onWillDestroy,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { sortBy } from "@web/core/utils/collections/arrays";
import { ErrorHandler } from "@web/core/utils/components";
const OVERLAY_ITEMS = [];
export const OVERLAY_SYMBOL = Symbol("Overlay");

/**
 * Wrapper for a single overlay entry (popover, dialog, bottom sheet, etc.).
 *
 * Tracks itself in a global `OVERLAY_ITEMS` stack for nested click-away
 * containment checks. Injects an `OVERLAY_SYMBOL` into child env so
 * descendants can test whether a click target is "inside" the overlay tree.
 */
class OverlayItem extends Component {
    static template = "web.OverlayContainer.Item";
    static components = {};
    static props = {
        component: { type: Function },
        props: { type: Object },
        env: { type: Object, optional: true },
    };

    setup() {
        this.rootRef = useRef("rootRef");

        OVERLAY_ITEMS.push(this);
        onWillDestroy(() => {
            const index = OVERLAY_ITEMS.indexOf(this);
            OVERLAY_ITEMS.splice(index, 1);
        });

        if (this.props.env) {
            this.__owl__.childEnv = this.props.env;
        }

        useChildSubEnv({
            [OVERLAY_SYMBOL]: {
                contains: (target) => this.contains(target),
            },
        });
    }

    /** @returns {OverlayItem[]} this overlay and all overlays stacked above it */
    get subOverlays() {
        return OVERLAY_ITEMS.slice(OVERLAY_ITEMS.indexOf(this));
    }

    /**
     * @param {EventTarget} target
     * @returns {boolean} whether target is inside this overlay or any sub-overlay
     */
    contains(target) {
        return (
            this.rootRef.el?.contains(target) ||
            this.subOverlays.some((oi) => oi.rootRef.el?.contains(target))
        );
    }
}

/** Renders all active overlays sorted by sequence, scoped to a shadow root. */
export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler, OverlayItem };
    static props = { overlays: Object };

    setup() {
        this.root = useRef("root");
        this.state = useState({ rootEl: null });
        useEffect(
            () => {
                this.state.rootEl = this.root.el;
            },
            () => [this.root.el],
        );
    }

    /** @returns {Object[]} overlays sorted by ascending sequence */
    get sortedOverlays() {
        return sortBy(
            Object.values(this.props.overlays),
            (overlay) => overlay.sequence,
        );
    }

    /**
     * @param {Object} overlay
     * @returns {boolean} whether overlay belongs to this container's shadow root
     */
    isVisible(overlay) {
        return overlay.rootId === this.state.rootEl?.getRootNode()?.host?.id;
    }

    /**
     * @param {Object} overlay
     * @param {Error} error
     */
    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
