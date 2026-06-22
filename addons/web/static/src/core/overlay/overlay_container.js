import {
    Component,
    onWillDestroy,
    Plugin,
    signal,
    t,
    usePlugin,
    useProps,
    useScope,
} from "@odoo/owl";
import { useChildSubEnv } from "@web/owl2/utils";
import { ErrorHandler } from "@web/core/utils/components";
import { services } from "@web/core/services";
import { registry } from "@web/core/registry";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";

const OVERLAY_ITEMS = [];
export const OVERLAY_SYMBOL = Symbol("Overlay");

class OverlayItem extends Component {
    static template = "web.OverlayContainer.Item";

    componentClass = useProps.static("component", t.component());
    componentProps = useProps.static("props", t.object());
    parentScope = useProps.static("scope", t.object().optional());

    rootRef = signal.ref();

    setup() {
        OVERLAY_ITEMS.push(this);
        onWillDestroy(() => {
            const index = OVERLAY_ITEMS.indexOf(this);
            OVERLAY_ITEMS.splice(index, 1);
        });

        if (this.parentScope) {
            const currentScope = useScope();
            currentScope.pluginManager = this.parentScope.pluginManager;
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
            this.rootRef()?.contains(target) ||
            this.subOverlays.some((oi) => oi.rootRef()?.contains(target))
        );
    }
}

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler, OverlayItem };

    overlayPlugin = usePlugin(OverlayPlugin);
    root = signal.ref();

    isVisible(overlay) {
        return overlay.rootId === this.env?.rootId;
    }

    handleError(overlay, error) {
        overlay.remove();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}

export class OverlayManagerPlugin extends Plugin {
    setup() {
        registry
            .category("main_components")
            .add(OverlayContainer.name, { Component: OverlayContainer });

        onWillDestroy(() => {
            registry.category("main_components").remove(OverlayContainer.name);
        });
    }
}

services.add(OverlayManagerPlugin);
