import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
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
        fullRowToggler: { type: Boolean, optional: true },
    };
    static defaultProps = { expand: false, observeCollapseContent: false, fullRowToggler: false };

    setup() {
        useBuilderComponent();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.state = useState({
            expanded: this.props.expand,
        });
        this.tooltipText = undefined;
        this.isBackendRTL = localization.direction === "rtl";

        if (this.props.slots.collapse) {
            useVisibilityObserver("collapse-content", useApplyVisibility("collapse"));

            this.collapseContentId = uniqueId("builder_collapse_content_");
        }

        this.labelRef = useRef("label");
        this.rootRef = useRef("root");
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

        useEffect(() => refreshSublevelLines(this.rootRef.el));
    }

    getLevelClass() {
        return this.props.level ? `hb-row-sublevel hb-row-sublevel-${this.props.level}` : "";
    }

    onRowContentClick() {
        if (this.props.fullRowToggler) {
            this.toggleCollapseContent();
        }
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
        const labelEl = this.labelRef.el;
        if (this.tooltipText === undefined) {
            const isLabelTooLong = labelEl.offsetWidth < labelEl.scrollWidth;
            if (isLabelTooLong) {
                this.tooltipText = this.props.tooltip
                    ? `${this.props.label}\u00A0: ${this.props.tooltip}`
                    : this.props.label;
            } else if (this.props.tooltip) {
                this.tooltipText = this.props.tooltip;
            } else {
                this.tooltipText = "";
            }
        }
        if (this.tooltipText) {
            this.removeTooltip = this.tooltip.add(labelEl, {
                tooltip: this.tooltipText,
            });
        }
    }

    closeTooltip() {
        if (this.removeTooltip) {
            this.removeTooltip();
        }
    }
}

function refreshSublevelLines(rowEl) {
    const optionsContainerEl = rowEl?.closest(".options-container");
    if (!optionsContainerEl) {
        return;
    }
    alignSublevelLines(optionsContainerEl);
}

// Recompute the vertical connector line for nested rows:
// - Clear any previous offset on all rows.
// - Skip hidden rows to avoid zero-size measurements.
// - Align each connector elbow with the current label center.
// - When rows connect with a previous same-level row, stretch the line up to
//   that label center, unless the computed value already matches the CSS default.
function alignSublevelLines(optionsContainerEl) {
    const visibleRowEls = [...optionsContainerEl.querySelectorAll(".hb-row")].filter((rowEl) => {
        const labelEl = rowEl.querySelector(":scope > .hb-row-label");
        if (labelEl) {
            labelEl.style.removeProperty("--o-hb-row-sublevel-top");
            labelEl.style.removeProperty("--o-hb-row-sublevel-center");
        }
        return getComputedStyle(rowEl).display !== "none";
    });
    for (let index = 0; index < visibleRowEls.length; index++) {
        const rowEl = visibleRowEls[index];
        const level = getRowLevel(rowEl);
        if (!level) {
            continue;
        }
        const labelEl = rowEl.querySelector(":scope > .hb-row-label");
        if (!labelEl) {
            continue;
        }
        const rowTop = rowEl.getBoundingClientRect().top;
        setLineStyle(labelEl, "center", getLabelCenter(labelEl) - rowTop);
        const previousRowEl = visibleRowEls[index - 1];
        if (!previousRowEl) {
            continue;
        }
        const previousLevel = getRowLevel(previousRowEl);
        const rowGap =
            rowEl.getBoundingClientRect().top - previousRowEl.getBoundingClientRect().bottom;
        if (previousLevel === level && Math.abs(rowGap) <= 1) {
            applyLineOffset(rowEl, previousRowEl);
            continue;
        }
        if (previousLevel <= level) {
            continue;
        }
        for (let previousIndex = index - 1; previousIndex >= 0; previousIndex--) {
            if (getRowLevel(visibleRowEls[previousIndex]) === level) {
                // Stretch the line up to the previous sibling of the same level.
                applyLineOffset(rowEl, visibleRowEls[previousIndex]);
                break;
            }
        }
    }
}

function applyLineOffset(rowEl, previousRowEl) {
    const labelEl = rowEl.querySelector(":scope > .hb-row-label");
    const previousLabelEl = previousRowEl.querySelector(":scope > .hb-row-label");
    if (!labelEl || !previousLabelEl) {
        return;
    }
    const offset = getLabelCenter(previousLabelEl) - rowEl.getBoundingClientRect().top;
    if (offset < 0) {
        setLineStyle(labelEl, "top", offset);
    }
}

function getLabelCenter(labelEl) {
    const { top, bottom, height = bottom - top } = labelEl.getBoundingClientRect();
    return top + height / 2;
}

function setLineStyle(el, property, value) {
    const propertyName = `--o-hb-row-sublevel-${property}`;
    const defaultValue = parseFloat(
        getComputedStyle(el).getPropertyValue(
            propertyName.replace("-sublevel-", "-sublevel-default-")
        )
    );
    if (Math.abs(value - defaultValue) <= 0.5) {
        el.style.removeProperty(propertyName);
        return;
    }
    el.style.setProperty(propertyName, `${value}px`);
}

function getRowLevel(rowEl) {
    const sublevelClass = [...rowEl.classList].find((className) =>
        className.startsWith("hb-row-sublevel-")
    );
    if (!sublevelClass) {
        return 0;
    }
    return parseInt(sublevelClass.replace("hb-row-sublevel-", ""), 10) || 0;
}

export { refreshSublevelLines };
