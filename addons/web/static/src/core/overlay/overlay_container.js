import {
    Component,
    onWillDestroy,
    onWillRender,
    toRaw,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { sortBy } from "@web/core/utils/arrays";
import { ErrorHandler } from "@web/core/utils/components";
import { sprintf } from "../utils/strings";

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

const STATIC_OVERLAYS = 10;
const tmp = `
    <t t-set="overlay" t-value="this.staticList[%(index)s]"/>
    <ErrorHandler t-if="overlay and isVisible(overlay)" onError="(error) => this.handleError(overlay, error)">
        <OverlayItem env="overlay.env" component="overlay.component" props="overlay.props"/>
    </ErrorHandler>`;

const tmps = [];
for (let i = 0; i < STATIC_OVERLAYS; i++) {
    tmps.push(sprintf(tmp, { index: i }));
}
const STATICS_TEMPLATE = xml`<t>${tmps.join("\n")}</t>`;

export class OverlayContainer extends Component {
    static template = "web.OverlayContainer";
    static components = { ErrorHandler, OverlayItem };
    static props = { overlays: Object };

    setup() {
        this.staticTemplate = STATICS_TEMPLATE;
        this.static = useState({ list: new Array(STATIC_OVERLAYS) });

        onWillRender(() => {
            this.computeOverlays(this._sortedOverlays);
        });

        this.root = useRef("root");
        this.state = useState({ rootEl: null });
        useEffect(
            () => {
                this.state.rootEl = this.root.el;
            },
            () => [this.root.el]
        );
    }

    computeOverlays(overlayList) {
        const prevMap = this.map || {};
        this.map = {};
        this.sortedOverlays = [];
        for (const o of overlayList) {
            this.map[o.id] = o;
        }

        const staticList = toRaw(this.static.list);
        const freeIndeces = [];
        const staticMap = {};
        for (let i = staticList.length - 1; i >= 0; i--) {
            const o = staticList[i];
            if (!o) {
                freeIndeces.push(i);
            } else if (o.id in prevMap && !(o.id in this.map)) {
                staticList[i] = undefined;
                freeIndeces.push(i);
            } else {
                staticMap[o.id] = true;
            }
        }
        for (const id in this.map) {
            if (id in staticMap) {
                continue;
            }
            const o = this.map[id];
            if (freeIndeces.length && o.sequence === 0) {
                const i = freeIndeces.pop();
                staticList[i] = o;
            } else {
                this.sortedOverlays.push(o);
            }
        }
        this.staticList = this.static.list;
    }

    get _sortedOverlays() {
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
