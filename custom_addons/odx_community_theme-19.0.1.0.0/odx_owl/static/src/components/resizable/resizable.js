/** @odoo-module **/

import {
    Component,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function equalLayout(length) {
    if (!length) {
        return [];
    }
    return Array.from({ length }, () => 100 / length);
}

function normalizeLayout(layout, length) {
    if (!length) {
        return [];
    }
    const source = Array.isArray(layout) ? layout.slice(0, length) : [];
    if (source.length !== length) {
        return equalLayout(length);
    }
    const values = source.map((value) => Math.max(0, Number(value) || 0));
    const total = values.reduce((sum, value) => sum + value, 0);
    if (!total) {
        return equalLayout(length);
    }
    return values.map((value) => (value / total) * 100);
}

function computePanelLayout(panels, providedLayout = null) {
    if (!panels.length) {
        return [];
    }
    if (Array.isArray(providedLayout) && providedLayout.length === panels.length) {
        return normalizeLayout(providedLayout, panels.length);
    }
    const preferred = panels.map((panel) => panel.getPreferredSize());
    const explicitTotal = preferred.reduce((sum, value) => sum + (value ?? 0), 0);
    const missing = preferred.filter((value) => value === null || value === undefined).length;
    if (!explicitTotal && missing === panels.length) {
        return equalLayout(panels.length);
    }
    const remaining = missing ? Math.max(0, 100 - explicitTotal) / missing : 0;
    const filled = preferred.map((value) => value ?? remaining);
    return normalizeLayout(filled, panels.length);
}

export class ResizablePanelGroup extends Component {
    static template = "odx_owl.ResizablePanelGroup";
    static props = {
        className: { type: String, optional: true },
        defaultLayout: { type: Array, optional: true },
        direction: { type: String, optional: true },
        dir: { type: String, optional: true },
        layout: { type: Array, optional: true },
        onLayoutChange: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        defaultLayout: [],
        direction: "horizontal",
        layout: undefined,
        tag: "div",
    };

    setup() {
        const self = this;
        this.rootRef = useRef("rootRef");
        this.panels = [];
        this.handles = [];
        this.state = useState({
            activeHandleId: null,
            dragStart: null,
            layout: [],
        });

        useChildSubEnv({
            odxResizableGroup: {
                get direction() {
                    return self.props.direction;
                },
                get dir() {
                    return self.directionName;
                },
                getHandleOrientation: () => self.handleOrientation,
                getHandleValue: (handleId) => self.getHandleValue(handleId),
                getPanelSize: (panelId) => self.getPanelSize(panelId),
                registerHandle: (handleApi) => self.registerHandle(handleApi),
                registerPanel: (panelApi) => self.registerPanel(panelApi),
                resizeByKeyboard: (handleId, delta) => self.resizeByDelta(handleId, delta),
                startResize: (handleId, ev) => self.startResize(handleId, ev),
                unregisterHandle: (handleId) => self.unregisterHandle(handleId),
                unregisterPanel: (panelId) => self.unregisterPanel(panelId),
            },
        });

        useExternalListener(window, "pointermove", (ev) => this.onPointerMove(ev));
        useExternalListener(window, "pointerup", () => this.endResize());
        useExternalListener(window, "pointercancel", () => this.endResize());

        onWillUpdateProps((nextProps) => {
            if (Array.isArray(nextProps.layout) && nextProps.layout.length === this.panels.length) {
                this.state.layout = normalizeLayout(nextProps.layout, this.panels.length);
            }
        });
    }

    get classes() {
        return cn(
            "odx-resizable",
            {
                "odx-resizable--horizontal": this.props.direction !== "vertical",
                "odx-resizable--vertical": this.props.direction === "vertical",
            },
            this.props.className
        );
    }

    get directionName() {
        return resolveDirection(this.props.dir);
    }

    get currentLayout() {
        if (this.state.layout.length === this.panels.length && this.panels.length) {
            return this.state.layout;
        }
        const nextLayout = computePanelLayout(this.panels, this.props.layout || this.props.defaultLayout);
        if (nextLayout.length) {
            this.state.layout = nextLayout;
        }
        return nextLayout;
    }

    get handleOrientation() {
        return this.props.direction === "vertical" ? "horizontal" : "vertical";
    }

    getPanelIndex(panelId) {
        return this.panels.findIndex((panel) => panel.id === panelId);
    }

    getPanelSize(panelId) {
        const index = this.getPanelIndex(panelId);
        return index === -1 ? null : this.currentLayout[index];
    }

    getHandleValue(handleId) {
        const index = this.handles.findIndex((handle) => handle.id === handleId);
        return index === -1 ? null : this.currentLayout[index];
    }

    notifyLayoutChange(layout) {
        this.props.onLayoutChange?.(layout);
    }

    registerHandle(handleApi) {
        if (!this.handles.find((handle) => handle.id === handleApi.id)) {
            this.handles.push(handleApi);
        }
    }

    registerPanel(panelApi) {
        if (!this.panels.find((panel) => panel.id === panelApi.id)) {
            this.panels.push(panelApi);
            this.state.layout = computePanelLayout(
                this.panels,
                this.props.layout || this.props.defaultLayout
            );
        }
    }

    resizeByDelta(handleId, deltaPercent, useCurrent = true) {
        const handleIndex = this.handles.findIndex((handle) => handle.id === handleId);
        if (handleIndex === -1) {
            return;
        }
        const beforePanel = this.panels[handleIndex];
        const afterPanel = this.panels[handleIndex + 1];
        if (!beforePanel || !afterPanel) {
            return;
        }
        const baseLayout = useCurrent
            ? [...this.currentLayout]
            : [...(this.state.dragStart?.layout || this.currentLayout)];
        const total = baseLayout[handleIndex] + baseLayout[handleIndex + 1];
        const lowerBound = Math.max(beforePanel.getMinSize(), total - afterPanel.getMaxSize());
        const upperBound = Math.min(beforePanel.getMaxSize(), total - afterPanel.getMinSize());
        const nextBefore = clamp(baseLayout[handleIndex] + deltaPercent, lowerBound, upperBound);
        const nextAfter = total - nextBefore;
        const nextLayout = [...baseLayout];
        nextLayout[handleIndex] = nextBefore;
        nextLayout[handleIndex + 1] = nextAfter;
        this.state.layout = nextLayout;
        this.notifyLayoutChange(nextLayout);
    }

    startResize(handleId, ev) {
        const rect = this.rootRef.el?.getBoundingClientRect();
        if (!rect) {
            return;
        }
        this.state.activeHandleId = handleId;
        this.state.dragStart = {
            layout: [...this.currentLayout],
            pointer:
                this.props.direction === "vertical" ? ev.clientY : ev.clientX,
            size:
                this.props.direction === "vertical" ? rect.height : rect.width,
        };
        ev.preventDefault();
    }

    onPointerMove(ev) {
        if (!this.state.activeHandleId || !this.state.dragStart?.size) {
            return;
        }
        ev.preventDefault();
        const pointer = this.props.direction === "vertical" ? ev.clientY : ev.clientX;
        const deltaPercent =
            ((pointer - this.state.dragStart.pointer) / this.state.dragStart.size) * 100;
        this.resizeByDelta(this.state.activeHandleId, deltaPercent, false);
    }

    endResize() {
        if (!this.state.activeHandleId) {
            return;
        }
        this.state.activeHandleId = null;
        this.state.dragStart = null;
    }

    unregisterHandle(handleId) {
        this.handles = this.handles.filter((handle) => handle.id !== handleId);
    }

    unregisterPanel(panelId) {
        const panelIndex = this.getPanelIndex(panelId);
        if (panelIndex === -1) {
            return;
        }
        this.panels = this.panels.filter((panel) => panel.id !== panelId);
        const nextLayout = this.currentLayout.filter((_, index) => index !== panelIndex);
        this.state.layout = normalizeLayout(nextLayout, this.panels.length);
    }
}

export class ResizablePanel extends Component {
    static template = "odx_owl.ResizablePanel";
    static props = {
        className: { type: String, optional: true },
        defaultSize: { type: Number, optional: true },
        maxSize: { type: Number, optional: true },
        minSize: { type: Number, optional: true },
        panelId: { type: String, optional: true },
        size: { type: Number, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        defaultSize: undefined,
        maxSize: 90,
        minSize: 10,
        tag: "div",
    };

    setup() {
        this.state = useState({
            id: this.props.panelId || nextId("odx-resizable-panel"),
        });

        useEffect(
            () => {
                const api = {
                    id: this.state.id,
                    getMaxSize: () => this.getMaxSize(),
                    getMinSize: () => this.getMinSize(),
                    getPreferredSize: () => this.getPreferredSize(),
                };
                this.env.odxResizableGroup.registerPanel(api);
                return () => this.env.odxResizableGroup.unregisterPanel(this.state.id);
            },
            () => []
        );
    }

    get classes() {
        return cn("odx-resizable__panel", this.props.className);
    }

    get panelSize() {
        return this.env.odxResizableGroup.getPanelSize(this.state.id);
    }

    get panelStyle() {
        return `flex: ${this.panelSize ?? 1} 1 0px;`;
    }

    getMaxSize() {
        return Number(this.props.maxSize) || 90;
    }

    getMinSize() {
        return Number(this.props.minSize) || 10;
    }

    getPreferredSize() {
        if (this.props.size !== undefined) {
            return Number(this.props.size) || 0;
        }
        if (this.props.defaultSize !== undefined) {
            return Number(this.props.defaultSize) || 0;
        }
        return null;
    }
}

export class ResizableHandle extends Component {
    static template = "odx_owl.ResizableHandle";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        withHandle: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Resize panels",
        className: "",
        disabled: false,
        withHandle: false,
    };

    setup() {
        this.state = useState({
            id: nextId("odx-resizable-handle"),
        });

        useEffect(
            () => {
                this.env.odxResizableGroup.registerHandle({ id: this.state.id });
                return () => this.env.odxResizableGroup.unregisterHandle(this.state.id);
            },
            () => []
        );
    }

    get classes() {
        return cn(
            "odx-resizable__handle",
            {
                "odx-resizable__handle--horizontal": this.orientation === "horizontal",
                "odx-resizable__handle--vertical": this.orientation === "vertical",
                "odx-resizable__handle--with-grip": this.props.withHandle,
            },
            this.props.className
        );
    }

    get isDisabled() {
        return this.props.disabled;
    }

    get orientation() {
        return this.env.odxResizableGroup.getHandleOrientation();
    }

    get ariaValueNow() {
        const value = this.env.odxResizableGroup.getHandleValue(this.state.id);
        return value === null ? undefined : Math.round(value);
    }

    onKeydown(ev) {
        if (this.isDisabled) {
            return;
        }
        const horizontal = this.orientation === "horizontal";
        const isRtl = !horizontal && isRtlDirection(this.env.odxResizableGroup.dir);
        const negativeKeys = horizontal
            ? ["ArrowUp"]
            : [isRtl ? "ArrowRight" : "ArrowLeft"];
        const positiveKeys = horizontal
            ? ["ArrowDown"]
            : [isRtl ? "ArrowLeft" : "ArrowRight"];
        if (!negativeKeys.includes(ev.key) && !positiveKeys.includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        const delta = positiveKeys.includes(ev.key) ? 5 : -5;
        this.env.odxResizableGroup.resizeByKeyboard(this.state.id, delta);
    }

    onPointerDown(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxResizableGroup.startResize(this.state.id, ev);
    }
}
