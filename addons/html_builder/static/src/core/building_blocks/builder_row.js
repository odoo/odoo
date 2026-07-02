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
// - When needed, stretch a row line up to the previous row it should connect to.
function alignSublevelLines(optionsContainerEl) {
    const rowEls = [...optionsContainerEl.querySelectorAll(".hb-row")];
    if (!rowEls.length) {
        return;
    }
    const visibleRowEls = [];
    for (const rowEl of rowEls) {
        const labelEl = rowEl.querySelector(":scope > .hb-row-label");
        if (labelEl) {
            labelEl.style.removeProperty("--o-hb-row-sublevel-base-offset");
            labelEl.style.removeProperty("--o-hb-row-sublevel-top");
            labelEl.style.removeProperty("--o-hb-row-sublevel-offset");
        }
        const rowStyle = getComputedStyle(rowEl);
        if (rowStyle.display === "none") {
            continue;
        }
        const level = getRowLevel(rowEl);
        const rowRect = rowEl.getBoundingClientRect();
        const labelRect = labelEl?.getBoundingClientRect();
        const baseSublevelOffset = getBaseSublevelOffset(rowStyle, rowRect, labelRect);
        if (labelEl && level) {
            labelEl.style.setProperty("--o-hb-row-sublevel-base-offset", `${baseSublevelOffset}px`);
        }
        const labelTextCenter =
            labelEl && level ? getLabelTextCenter(labelEl, labelRect) : undefined;
        const sublevelOffset =
            labelTextCenter === undefined
                ? 0
                : applySublevelOffset(labelEl, rowRect, baseSublevelOffset, labelTextCenter);
        visibleRowEls.push({
            labelEl,
            rowRect,
            labelRect,
            level,
            baseSublevelOffset,
            sublevelOffset,
        });
    }
    for (let index = 0; index < visibleRowEls.length; index++) {
        const rowData = visibleRowEls[index];
        const previousRowData = visibleRowEls[index - 1];
        const { level } = rowData;
        if (!level || !previousRowData) {
            continue;
        }
        if (previousRowData.level <= level) {
            applyLineOffset(rowData, previousRowData);
            continue;
        }
        for (let previousIndex = index - 1; previousIndex >= 0; previousIndex--) {
            const previousSameLevelRowData = visibleRowEls[previousIndex];
            if (previousSameLevelRowData.level === level) {
                // Stretch the line up to the previous sibling of the same level.
                applyLineOffset(rowData, previousSameLevelRowData);
                break;
            }
        }
    }
}

function applyLineOffset(rowData, previousRowData) {
    const { labelEl, rowRect, baseSublevelOffset } = rowData;
    const { rowRect: previousRowRect } = previousRowData;
    if (!labelEl || !rowRect || !previousRowRect) {
        return;
    }
    const previousRowCenter = previousRowRect.top + previousRowRect.height * 0.5;
    const offset = previousRowCenter - rowRect.top - baseSublevelOffset;
    if (offset) {
        labelEl.style.setProperty("--o-hb-row-sublevel-top", `${offset}px`);
    }
}

function getLabelTextCenter(labelEl, labelRect) {
    const labelTextEl = labelEl.querySelector(":scope > .text-nowrap");
    if (!labelTextEl) {
        return;
    }
    const textRect = labelTextEl.getBoundingClientRect();
    return textRect.bottom - textRect.height * 0.5;
}

function applySublevelOffset(labelEl, rowRect, baseSublevelOffset, textCenter) {
    const bottomLine = rowRect.bottom + baseSublevelOffset;
    if (textCenter === undefined) {
        return 0;
    }
    // Align the connector "bottom line" with the text center.
    const offset = textCenter - bottomLine;
    if (offset) {
        labelEl.style.setProperty("--o-hb-row-sublevel-offset", `${offset}px`);
    }
    return offset;
}

function getBaseSublevelOffset(rowStyle, rowRect, labelRect) {
    if (rowRect && labelRect) {
        return labelRect.top + labelRect.height * 0.5 - rowRect.bottom;
    }
    const cssOffset = parseFloat(rowStyle.getPropertyValue("--o-hb-row-sublevel-base-offset"));
    return Number.isFinite(cssOffset) ? cssOffset : 0;
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
