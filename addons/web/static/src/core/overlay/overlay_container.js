import { Component, onWillDestroy, useChildSubEnv, useEffect, useRef, useState } from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { ErrorHandler } from "@web/core/utils/components";

const OVERLAY_ITEMS = [];
export const OVERLAY_SYMBOL = Symbol("Overlay");

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

    get subOverlays() {
        return OVERLAY_ITEMS.slice(OVERLAY_ITEMS.indexOf(this));
    }

    contains(target) {
        return (
            this.rootRef.el?.contains(target) ||
            this.subOverlays.some((oi) => oi.rootRef.el?.contains(target))
        );
    }
}

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
            () => [this.root.el]
        );
    }

    get sortedOverlays() {
        return sortBy(Object.values(this.props.overlays), (overlay) => overlay.sequence);
    }

    isVisible(overlay) {
        return overlay.rootId === this.state.rootEl?.getRootNode()?.host?.id;
    }

    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
