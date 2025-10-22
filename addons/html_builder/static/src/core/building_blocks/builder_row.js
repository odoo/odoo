import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { useTransition } from "@web/core/transition";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import {
    basicContainerBuilderComponentProps,
    useApplyVisibility,
    useBuilderComponent,
    useVisibilityObserver,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderRow extends Component {
    static template = "html_builder.BuilderRow";
    static components = { BuilderComponent };
    static props = {
        ...basicContainerBuilderComponentProps,
        label: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        slots: { type: Object, optional: true },
        level: { type: Number, optional: true },
        expand: { type: Boolean, optional: true },
        initialExpandAnim: { type: Boolean, optional: true },
        extraLabelClass: { type: String, optional: true },
        observeCollapseContent: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
    };
    static defaultProps = { expand: false, observeCollapseContent: false };

    setup() {
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.state = useState({
            expanded: this.props.expand,
        });
        this.hasTooltip = this.props.tooltip ? true : undefined;

        if (this.props.slots.collapse) {
            useVisibilityObserver("collapse-content", useApplyVisibility("collapse"));

            this.collapseContentId = uniqueId("builder_collapse_content_");
        }

        this.labelRef = useRef("label");
        this.collapseContentRef = useRef("collapse-content");
        let isMounted = false;

        onMounted(() => {
            if (this.props.initialExpandAnim) {
                setTimeout(() => {
                    this.toggleCollapseContent();
                }, 150);
            }
        });

        this.transition = useTransition({
            initialVisibility: this.props.expand,
            leaveDuration: 350,
            name: "hb-collapse-content",
        });

        useEffect(
            (stage) => {
                const isFirstMount = !isMounted;
                isMounted = true;
                const contentEl = this.collapseContentRef.el;
                if (!contentEl) {
                    return;
                }

                const setHeightAuto = () => {
                    contentEl.style.height = "auto";
                };

                // Skip transition on first mount if expand=true.
                if (isFirstMount && this.props.expand) {
                    setHeightAuto();
                    return;
                }

                switch (stage) {
                    case "enter-active": {
                        contentEl.style.height = contentEl.scrollHeight + "px";
                        contentEl.addEventListener("transitionend", setHeightAuto, { once: true });
                        break;
                    }
                    case "leave": {
                        // Collapse from current height to 0
                        contentEl.style.height = contentEl.scrollHeight + "px";
                        void contentEl.offsetHeight; // force reflow
                        contentEl.style.height = "0px";
                        break;
                    }
                }
            },
            () => [this.transition.stage]
        );
        this.tooltip = useService("tooltip");
    }

    getLevelClass() {
        return this.props.level ? `hb-row-sublevel hb-row-sublevel-${this.props.level}` : "";
    }

    toggleCollapseContent() {
        this.state.expanded = !this.state.expanded;
        this.transition.shouldMount = this.state.expanded;
    }

    get displayCollapseContent() {
        return this.transition.shouldMount || this.props.observeCollapseContent;
    }

    get collapseContentClass() {
        const isNotVisible = this.props.observeCollapseContent && !this.transition.shouldMount;
        return `${this.transition.className} ${isNotVisible ? "d-none" : ""}`;
    }

    openTooltip() {
        if (this.hasTooltip === undefined) {
            const labelEl = this.labelRef.el;
            this.hasTooltip = labelEl && labelEl.clientWidth < labelEl.scrollWidth;
        }
        if (this.hasTooltip) {
            const tooltip = this.props.tooltip || this.props.label;
            this.removeTooltip = this.tooltip.add(this.labelRef.el, { tooltip });
        }
    }

    closeTooltip() {
        if (this.removeTooltip) {
            this.removeTooltip();
        }
    }
}
