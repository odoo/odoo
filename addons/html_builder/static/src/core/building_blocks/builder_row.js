import { Component, onMounted, onPatched, proxy, signal, t, useEffect, useProps } from "@odoo/owl";
import { useTransition } from "@web/core/transition";
import { uniqueId } from "@web/core/utils/functions";
import {
    basicContainerBuilderComponentProps,
    useApplyVisibility,
    useBuilderComponent,
    useVisibilityObserver,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { animateExpand } from "./collapse_animation";

const builderRows = new WeakMap();
const initializedContainers = new WeakSet();

export class BuilderRow extends Component {
    static template = "html_builder.BuilderRow";
    static components = { BuilderComponent };

    props = useProps({
        ...basicContainerBuilderComponentProps,
        label: t.string().optional(),
        tooltip: t.string().optional(),
        slots: t.object().optional(),
        level: t.number().optional(),
        expand: t.boolean().optional(false),
        initialExpandAnim: t.boolean().optional(),
        extraLabelClass: t.string().optional(),
        observeCollapseContent: t.boolean().optional(false),
        disabled: t.boolean().optional(),
        fullRowToggler: t.boolean().optional(false),
    });

    rootRef = signal.ref();
    contentRef = signal.ref();
    collapseRef = signal.ref();
    collapseContentRef = signal.ref();

    setup() {
        useBuilderComponent(this.props);
        const applyVisibility = useApplyVisibility(this.rootRef);
        useVisibilityObserver(this.contentRef, (hasContent) => {
            applyVisibility(hasContent);
            refreshSublevelRows(this.rootRef());
        });

        this.state = proxy({
            expanded: this.props.expand,
            sublevelIds: null,
            hidden: null,
        });
        this.rowId = uniqueId("builder_row_");
        this.expandAnimations = [];

        if (this.props.slots.collapse) {
            const applyCollapseVisibility = useApplyVisibility(this.collapseRef);
            let hadContent;
            useVisibilityObserver(this.collapseContentRef, (hasContent) => {
                applyCollapseVisibility(hasContent);
                if (this.props.observeCollapseContent && hadContent === false && hasContent) {
                    this.state.expanded = true;
                    this.transition.shouldMount = true;
                }
                hadContent = hasContent;
            });

            this.collapseContentId = uniqueId("builder_collapse_content_");
        }

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
            leaveDuration: 150,
            name: "o_hb_collapse_content",
        });

        useEffect(() => {
            const expanded = this.state.expanded;
            const contentEl = this.collapseContentRef();
            if (!contentEl) {
                return;
            }
            const isFirstMount = !isMounted;
            isMounted = true;

            const setHeightAuto = () => {
                contentEl.style.height = "auto";
            };

            // Skip transition on first mount if expand=true.
            if (isFirstMount && this.props.expand) {
                setHeightAuto();
                return;
            }

            if (expanded) {
                contentEl.classList.remove("d-none");
                contentEl.style.height = "0px";
                void contentEl.offsetHeight; // force reflow
                contentEl.style.height = contentEl.scrollHeight + "px";
                contentEl.addEventListener("transitionend", setHeightAuto, { once: true });
                return () => contentEl.removeEventListener("transitionend", setHeightAuto);
            }
            // Collapse from current height to 0
            contentEl.style.height = contentEl.scrollHeight + "px";
            void contentEl.offsetHeight; // force reflow
            contentEl.style.height = "0px";
        });

        useEffect(() => {
            const rowEl = this.rootRef();
            if (!rowEl) {
                return;
            }
            const optionsContainerEl = rowEl.closest(".o_hb_options_container");
            builderRows.set(rowEl, this);
            refreshSublevelRows(rowEl);
            return () => {
                this.expandAnimations.forEach((animation) => animation.cancel());
                builderRows.delete(rowEl);
                this.state.sublevelIds = null;
                this.state.hidden = null;
                refreshSublevelRows(optionsContainerEl);
            };
        });
        onPatched(() => refreshSublevelRows(this.rootRef()));
    }

    getLevelClass() {
        return this.props.level ? `o_hb_row_sublevel o_hb_row_sublevel_${this.props.level}` : "";
    }

    onRowContentClick() {
        if (this.props.fullRowToggler) {
            this.toggleCollapseContent();
        }
    }

    toggleCollapseContent() {
        if (!this.props.slots.collapse && !this.state.sublevelIds) {
            return;
        }
        this.state.expanded = !this.state.expanded;
        if (this.props.slots.collapse) {
            this.transition.shouldMount = this.state.expanded;
        }
        refreshSublevelRows(this.rootRef());
    }

    get displayCollapseContent() {
        return this.transition.shouldMount || this.props.observeCollapseContent;
    }

    get collapseContentClass() {
        const isNotVisible = this.props.observeCollapseContent && !this.transition.shouldMount;
        return `${this.transition.className} ${isNotVisible ? "d-none" : ""}`;
    }
}

async function refreshSublevelRows(rowEl) {
    const optionsContainerEl = rowEl?.closest(".o_hb_options_container");
    if (!optionsContainerEl) {
        return;
    }
    await Promise.resolve();
    if (!optionsContainerEl.isConnected) {
        return;
    }
    const rowEls = [...optionsContainerEl.querySelectorAll(".o_hb_row")].filter(
        (rowEl) =>
            rowEl.closest(".o_hb_options_container") === optionsContainerEl &&
            !rowEl.closest(".o_hb_collapse_content")
    );
    if (!rowEls.length) {
        initializedContainers.delete(optionsContainerEl);
        return;
    }
    const groups = new Map();
    const parentRows = new Map();
    let parentRow;
    for (const rowEl of rowEls) {
        const row = builderRows.get(rowEl);
        if (!row) {
            continue;
        }
        if (!row.props.level) {
            parentRow =
                row.props.label?.trim() && !row.props.slots.collapse && !rowEl.closest(".d-none")
                    ? row
                    : null;
            groups.set(row, []);
        } else if (parentRow) {
            if (!rowEl.closest(".d-none")) {
                groups.get(parentRow).push(row.rowId);
            }
            parentRows.set(row, parentRow);
        }
    }
    for (const [row, ids] of groups) {
        const previousIds = row.state.sublevelIds?.split(" ");
        if (
            !row.props.slots.collapse &&
            initializedContainers.has(optionsContainerEl) &&
            ids.some((id) => !previousIds?.includes(id))
        ) {
            row.state.expanded = true;
        }
        row.state.sublevelIds = ids.join(" ");
    }
    for (const rowEl of rowEls) {
        const row = builderRows.get(rowEl);
        if (row) {
            const parentIds = parentRows.get(row)?.state.sublevelIds?.split(" ") || [];
            rowEl.classList.toggle("o_hb_row_group_child", parentIds.includes(row.rowId));
            rowEl.classList.toggle("o_hb_row_group_first", parentIds[0] === row.rowId);
            rowEl.classList.toggle("o_hb_row_group_last", parentIds.at(-1) === row.rowId);
            const hidden = parentRows.has(row) && !parentRows.get(row).state.expanded;
            if (hidden !== row.state.hidden) {
                row.expandAnimations.forEach((animation) => animation.cancel());
                row.expandAnimations = [];
                for (const contentEl of [rowEl, row.collapseContentRef()].filter(Boolean)) {
                    contentEl.hidden = false;
                    if (
                        (!hidden || row.state.hidden !== null) &&
                        parentRows.has(row) &&
                        initializedContainers.has(optionsContainerEl)
                    ) {
                        const animation = animateExpand(contentEl, !hidden);
                        if (animation) {
                            row.expandAnimations.push(animation);
                            animation.addEventListener(
                                "finish",
                                () => {
                                    contentEl.hidden = hidden;
                                    animation.cancel();
                                    alignSublevelLines(optionsContainerEl);
                                },
                                { once: true }
                            );
                            continue;
                        }
                    }
                    contentEl.hidden = hidden;
                }
                row.state.hidden = hidden;
            }
        }
    }
    initializedContainers.add(optionsContainerEl);
    alignSublevelLines(optionsContainerEl);
}

// Recompute the vertical connector line for nested rows:
// - Clear any previous offset on all rows.
// - Skip hidden rows to avoid zero-size measurements.
// - When a row comes back to a shallower level after deeper rows, stretch its
//   line up to the last visible sibling of the same level.
function alignSublevelLines(optionsContainerEl) {
    const rowEls = [...optionsContainerEl.querySelectorAll(".o_hb_row")];
    if (!rowEls.length) {
        return;
    }
    const visibleRowEls = [];
    for (const rowEl of rowEls) {
        const labelEl = rowEl.querySelector(":scope > .o_hb_row_label");
        if (labelEl) {
            labelEl.style.removeProperty("--o-hb-row-sublevel-top");
        }
        if (getComputedStyle(rowEl).display !== "none" && !rowEl.closest("[hidden]")) {
            visibleRowEls.push(rowEl);
        }
    }
    for (let index = 0; index < visibleRowEls.length; index++) {
        const rowEl = visibleRowEls[index];
        const level = getRowLevel(rowEl);
        if (!level) {
            continue;
        }
        const previousRowEl = visibleRowEls[index - 1];
        if (!previousRowEl || getRowLevel(previousRowEl) <= level) {
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
    const labelEl = rowEl.querySelector(":scope > .o_hb_row_label");
    const previousLabelEl = previousRowEl.querySelector(":scope > .o_hb_row_label");
    if (!labelEl || !previousLabelEl) {
        return;
    }
    const offset =
        previousLabelEl.getBoundingClientRect().bottom - labelEl.getBoundingClientRect().top;
    if (offset < 0) {
        labelEl.style.setProperty("--o-hb-row-sublevel-top", `${offset}px`);
    }
}

function getRowLevel(rowEl) {
    const sublevelClass = [...rowEl.classList].find((className) =>
        className.startsWith("o_hb_row_sublevel_")
    );
    if (!sublevelClass) {
        return 0;
    }
    return parseInt(sublevelClass.replace("o_hb_row_sublevel_", ""), 10) || 0;
}

export { refreshSublevelRows };
