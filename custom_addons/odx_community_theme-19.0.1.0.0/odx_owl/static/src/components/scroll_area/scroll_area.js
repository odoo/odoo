/** @odoo-module **/

import { Component, onMounted, onRendered, useExternalListener, useRef, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class ScrollBar extends Component {
    static template = "odx_owl.ScrollBar";
    static props = {
        className: { type: String, optional: true },
        orientation: { type: String, optional: true },
        thumbStyle: { type: String, optional: true },
        visible: { type: Boolean, optional: true },
    };
    static defaultProps = {
        className: "",
        orientation: "vertical",
        thumbStyle: "",
        visible: false,
    };

    get classes() {
        return cn(
            "odx-scroll-area__scrollbar",
            {
                "odx-scroll-area__scrollbar--horizontal": this.props.orientation === "horizontal",
                "odx-scroll-area__scrollbar--vertical": this.props.orientation !== "horizontal",
            },
            this.props.className
        );
    }
}

export class ScrollArea extends Component {
    static template = "odx_owl.ScrollArea";
    static components = {
        ScrollBar,
    };
    static props = {
        className: { type: String, optional: true },
        viewportClassName: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        viewportClassName: "",
    };

    setup() {
        this.viewportRef = useRef("viewportRef");
        this.state = useState({
            horizontalThumbStyle: "",
            showHorizontal: false,
            showVertical: false,
            verticalThumbStyle: "",
        });

        const updateMetrics = () => this.updateMetrics();
        onMounted(updateMetrics);
        onRendered(updateMetrics);
        useExternalListener(window, "resize", updateMetrics);
    }

    get classes() {
        return cn("odx-scroll-area", this.props.className);
    }

    get viewportClasses() {
        return cn("odx-scroll-area__viewport", this.props.viewportClassName);
    }

    onScroll() {
        this.updateMetrics();
    }

    updateMetrics() {
        const viewport = this.viewportRef.el;
        if (!viewport) {
            return;
        }

        const verticalOverflow = viewport.scrollHeight > viewport.clientHeight + 1;
        const horizontalOverflow = viewport.scrollWidth > viewport.clientWidth + 1;

        let verticalThumbStyle = "";
        if (verticalOverflow) {
            const thumbHeight = Math.max(
                (viewport.clientHeight / viewport.scrollHeight) * viewport.clientHeight,
                18
            );
            const maxTop = viewport.clientHeight - thumbHeight;
            const top = viewport.scrollHeight - viewport.clientHeight
                ? (viewport.scrollTop / (viewport.scrollHeight - viewport.clientHeight)) * maxTop
                : 0;
            verticalThumbStyle = `height: ${thumbHeight}px; transform: translateY(${top}px);`;
        }

        let horizontalThumbStyle = "";
        if (horizontalOverflow) {
            const thumbWidth = Math.max(
                (viewport.clientWidth / viewport.scrollWidth) * viewport.clientWidth,
                18
            );
            const maxLeft = viewport.clientWidth - thumbWidth;
            const left = viewport.scrollWidth - viewport.clientWidth
                ? (viewport.scrollLeft / (viewport.scrollWidth - viewport.clientWidth)) * maxLeft
                : 0;
            horizontalThumbStyle = `width: ${thumbWidth}px; transform: translateX(${left}px);`;
        }

        this.state.showVertical = verticalOverflow;
        this.state.showHorizontal = horizontalOverflow;
        this.state.verticalThumbStyle = verticalThumbStyle;
        this.state.horizontalThumbStyle = horizontalThumbStyle;
    }
}
