// @ts-check
/** @odoo-module native */

import {
    onWillUnmount,
    onWillUpdateProps,
    useComponent,
    useEffect,
    useExternalListener,
    useRef,
} from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useThrottleForAnimation } from "@web/core/utils/timing";

const log = makeLogger("web.components.resizable_panel");
const DEFAULT_SPACING = 10;
export const DEFAULT_PANEL_WIDTH = 400;

/**
 * @typedef {"start" | "end"} ResizeSide
 * @typedef {Object} UseResizableParams
 * @property {string | import("@odoo/owl").Ref<HTMLElement>} containerRef
 * @property {string | import("@odoo/owl").Ref<HTMLElement>} handleRef
 * @property {(props: Object) => number} [getInitialWidth]
 * @property {(props: Object) => number} [getMinWidth]
 * @property {(width: number) => void} [onResize]
 * @property {(props: Object) => ResizeSide} [getResizeSide]
 */

class ResizeController {
    /**
     * @param {import("@odoo/owl").Ref<HTMLElement>} containerRef
     * @param {import("@odoo/owl").Ref<HTMLElement>} handleRef
     * @param {{ getMinWidth: Function, getResizeSide: Function, getInitialWidth: Function, onResize: Function }} params
     * @param {Object} props
     */
    constructor(containerRef, handleRef, params, props) {
        this.containerRef = containerRef;
        this.handleRef = handleRef;
        this.params = params;
        this.minWidth = params.getMinWidth(props);
        this.resizeSide = params.getResizeSide(props);
        this.initialWidth = params.getInitialWidth(props);
        /** @type {{ direction: 1 | -1, fixedEdge: number, limit: number, spacing: number, pointerId: number } | null} */
        this.drag = null;
        this.onPointerDown = this.onPointerDown.bind(this);
        this.onPointerMove = this.onPointerMove.bind(this);
        this.onPointerUp = this.onPointerUp.bind(this);
    }

    /** @param {Object} nextProps */
    applyProps(nextProps) {
        const previousInitialWidth = this.initialWidth;
        this.minWidth = this.params.getMinWidth(nextProps);
        this.resizeSide = this.params.getResizeSide(nextProps);
        this.initialWidth = this.params.getInitialWidth(nextProps);
        const currentWidth = this.currentWidth();
        const nextWidth = this.clampWidth(
            this.initialWidth !== previousInitialWidth
                ? this.initialWidth
                : currentWidth,
        );
        if (nextWidth !== currentWidth) {
            this.resize(nextWidth);
        }
    }

    /**
     * @param {HTMLElement} handle
     * @returns {() => void}
     */
    attach(handle) {
        this.resize(this.clampWidth(this.initialWidth));
        handle.addEventListener("pointerdown", this.onPointerDown);
        handle.style.touchAction = "none";
        return () => {
            handle.removeEventListener("pointerdown", this.onPointerDown);
            this.onPointerUp();
        };
    }

    /** @param {PointerEvent} ev */
    onPointerDown(ev) {
        if (!this.containerRef.el || ev.button !== 0 || this.drag) {
            return;
        }
        const docDirection = getComputedStyle(this.containerRef.el).direction;
        const direction =
            (docDirection === "ltr" && this.resizeSide === "end") ||
            (docDirection === "rtl" && this.resizeSide === "start")
                ? 1
                : -1;
        this.drag = {
            pointerId: ev.pointerId,
            direction,
            fixedEdge: this.containerRect()[direction === 1 ? "left" : "right"],
            limit: this.limitWidth(),
            spacing: this.handleSpacing(),
        };
        log.logic("resize started", () => ({ pointerId: ev.pointerId }));
        document.body.classList.add("pe-none", "user-select-none");
        try {
            this.handleRef.el?.setPointerCapture(ev.pointerId);
        } catch {}
        document.addEventListener("pointermove", this.onPointerMove);
        document.addEventListener("pointerup", this.onPointerUp);
        document.addEventListener("pointercancel", this.onPointerUp);
    }

    /** @param {PointerEvent} [ev] */
    onPointerUp(ev) {
        if (!this.drag || (ev && ev.pointerId !== this.drag.pointerId)) {
            return;
        }
        try {
            this.handleRef.el?.releasePointerCapture(this.drag.pointerId);
        } catch {}
        log.logic("resize stopped");
        this.drag = null;
        document.body.classList.remove("pe-none", "user-select-none");
        document.removeEventListener("pointermove", this.onPointerMove);
        document.removeEventListener("pointerup", this.onPointerUp);
        document.removeEventListener("pointercancel", this.onPointerUp);
    }

    /** @param {PointerEvent} ev */
    onPointerMove(ev) {
        if (
            !this.drag ||
            ev.pointerId !== this.drag.pointerId ||
            !this.containerRef.el
        ) {
            return;
        }
        const { direction, fixedEdge, limit, spacing } = this.drag;
        const newWidth = (ev.clientX - fixedEdge) * direction;
        this.resize(this.clampWidth(newWidth + spacing, limit, spacing));
    }

    onWindowResize() {
        if (!this.containerRef.el) {
            return;
        }
        const limit = this.limitWidth();
        if (this.containerRect().width >= limit) {
            this.resize(this.finalWidth(limit));
        }
    }

    /** @returns {number} */
    handleSpacing() {
        return this.handleRef.el ? this.handleRef.el.offsetWidth / 2 : DEFAULT_SPACING;
    }

    /**
     * @param {number} width
     * @param {number} [limit]
     * @param {number} [spacing]
     * @returns {number}
     */
    clampWidth(width, limit = this.limitWidth(), spacing = this.handleSpacing()) {
        return Math.min(Math.max(this.minWidth, width), limit - spacing);
    }

    /**
     * @param {number} targetContainerWidth
     * @returns {number}
     */
    finalWidth(targetContainerWidth) {
        return this.clampWidth(targetContainerWidth + this.handleSpacing());
    }

    /** @returns {{ left: number, right: number, width: number }} */
    containerRect() {
        return /** @type {HTMLElement} */ (
            this.containerRef.el
        ).getBoundingClientRect();
    }

    /** @returns {number} */
    currentWidth() {
        const styled = Number.parseFloat(this.containerRef.el?.style.width ?? "");
        if (Number.isFinite(styled)) {
            return styled;
        }
        return this.containerRef.el ? this.containerRect().width : this.initialWidth;
    }

    /** @returns {number} */
    limitWidth() {
        const offsetParent = /** @type {HTMLElement | null} */ (
            this.containerRef.el?.offsetParent ?? null
        );
        return offsetParent ? offsetParent.offsetWidth : window.innerWidth;
    }

    /** @param {number} width */
    resize(width) {
        if (!this.containerRef.el) {
            return;
        }
        this.containerRef.el.style.setProperty("width", `${width}px`);
        this.params.onResize(width);
    }
}

/** @param {UseResizableParams} params */
export function useResizable({
    containerRef: _containerRef,
    handleRef: _handleRef,
    getInitialWidth = (_props) => DEFAULT_PANEL_WIDTH,
    getMinWidth = (_props) => DEFAULT_PANEL_WIDTH,
    onResize = (_width) => {},
    getResizeSide = (_props) => "end",
}) {
    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    const containerRef =
        typeof _containerRef == "string" ? useRef(_containerRef) : _containerRef;
    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    const handleRef = typeof _handleRef == "string" ? useRef(_handleRef) : _handleRef;
    const component = useComponent();
    const controller = new ResizeController(
        containerRef,
        handleRef,
        { getInitialWidth, getMinWidth, onResize, getResizeSide },
        component.props,
    );

    useExternalListener(
        window,
        "resize",
        useThrottleForAnimation(() => controller.onWindowResize()),
    );

    useEffect(
        (el) => (el ? controller.attach(el) : undefined),
        () => [handleRef.el],
    );

    onWillUpdateProps((nextProps) => controller.applyProps(nextProps));

    onWillUnmount(() => {
        if (controller.drag) {
            controller.onPointerUp();
        }
    });
}
