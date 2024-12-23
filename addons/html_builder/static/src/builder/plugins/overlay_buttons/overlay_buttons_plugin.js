import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { getScrollingElement, getScrollingTarget } from "@web/core/utils/scrolling";
import { OverlayButtons } from "./overlay_buttons";
import {
    sizingY,
    sizingX,
    sizingGrid,
} from "@html_builder/builder/plugins/builder_overlay/builder_overlay";

// Moving with the arrows.
const moveUpOrDown = {
    selector: [
        "section",
        ".s_accordion .accordion-item",
        ".s_showcase .row .row:not(.s_col_no_resize) > div",
        ".s_hr",
        // In snippets files
        ".s_pricelist_boxed_item",
        ".s_pricelist_cafe_item",
        ".s_product_catalog_dish",
        ".s_timeline_list_row",
        ".s_timeline_row",
    ].join(", "),
};

const moveLeftOrRight = {
    selector: [
        ".row:not(.s_col_no_resize) > div",
        ".nav-item",
        ".s_timeline_card", // timeline TODO custom function, other plugin ?
    ].join(", "),
    exclude: ".s_showcase .row .row > div",
};

function isMovable(el) {
    const canMoveUpOrDown = el.matches(moveUpOrDown.selector);
    const canMoveLeftOrRight =
        el.matches(moveLeftOrRight.selector) && !el.matches(moveLeftOrRight.exclude);
    return canMoveUpOrDown || canMoveLeftOrRight;
}

function isResizable(el) {
    const isResizableY = el.matches(sizingY.selector) && !el.matches(sizingY.exclude);
    const isResizableX = el.matches(sizingX.selector) && !el.matches(sizingX.exclude);
    const isResizableGrid = el.matches(sizingGrid.selector) && !el.matches(sizingGrid.exclude);
    return isResizableY || isResizableX || isResizableGrid;
}

export class OverlayButtonsPlugin extends Plugin {
    static id = "overlayButtons";
    static dependencies = ["selection", "overlay", "history"];
    resources = {
        step_added_handlers: this.refreshButtons.bind(this),
        change_current_options_containers_listeners: this.addOverlayButtons.bind(this),
        on_mobile_preview_clicked: this.refreshButtons.bind(this),
    };

    setup() {
        // TODO find how to not overflow the mobile preview.
        this.iframe = this.editable.ownerDocument.defaultView.frameElement;
        this.overlay = this.dependencies.overlay.createOverlay(OverlayButtons, {
            positionOptions: {
                position: "top-middle",
                onPositioned: (overlayEl, position) => {
                    const iframeRect = this.iframe.getBoundingClientRect();
                    if (position.top < iframeRect.top) {
                        const targetRect = this.target.getBoundingClientRect();
                        const newTop = iframeRect.top + targetRect.bottom + 15;
                        position.top = newTop;
                        overlayEl.style.top = `${newTop}px`;
                    }
                    return;
                },
                margin: 15,
                flip: false,
            },
            closeOnPointerdown: false,
        });
        this.target = null;
        this.state = reactive({
            isVisible: true,
            buttons: [],
        });

        this.resizeObserver = new ResizeObserver(() => {
            this.overlay.updatePosition();
        });

        // TODO duplicate of builderOverlay => extract somewhere
        // Recompute the buttons when the window is resized.
        this.refresh = throttleForAnimation(this.refreshButtons.bind(this));
        this.addDomListener(window, "resize", this.refresh);

        // On keydown, hide the buttons and then show them again when the mouse
        // moves.
        const onMouseMoveOrDown = throttleForAnimation((ev) => {
            this.toggleVisibility(true);
            ev.currentTarget.removeEventListener("mousemove", onMouseMoveOrDown);
            ev.currentTarget.removeEventListener("mousedown", onMouseMoveOrDown);
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            this.toggleVisibility(false);
            ev.currentTarget.addEventListener("mousemove", onMouseMoveOrDown);
            ev.currentTarget.addEventListener("mousedown", onMouseMoveOrDown);
        });

        // Hide the buttons when scrolling. Show them again when the scroll is
        // over.
        const scrollingElement = getScrollingElement(this.document);
        const scrollingTarget = getScrollingTarget(scrollingElement);
        this.addDomListener(
            scrollingTarget,
            "scroll",
            throttleForAnimation(() => {
                this.toggleVisibility(false);
                clearTimeout(this.scrollingTimeout);
                this.scrollingTimeout = setTimeout(() => {
                    this.toggleVisibility(true);
                }, 250);
            }),
            { capture: true }
        );

        this._cleanups.push(() => {
            this.removeOverlayButtons();
            this.resizeObserver.disconnect();
        });
    }

    refreshButtons() {
        if (!this.target) {
            return;
        }
        const buttons = [];
        for (const getOverlayButtons of this.getResource("get_overlay_buttons")) {
            buttons.push(...getOverlayButtons(this.target));
        }
        this.state.buttons = buttons;
    }

    toggleVisibility(show) {
        this.state.isVisible = show;
    }

    addOverlayButtons(optionsContainer) {
        this.removeOverlayButtons();

        // Find the innermost option neediing the overlay buttons.
        const optionWithOverlayButtons = optionsContainer.findLast((option) =>
            this.hasOverlayOptions(option.element)
        );
        if (optionWithOverlayButtons) {
            this.target = optionWithOverlayButtons.element;
            this.refreshButtons();
            this.overlay.open({
                target: optionWithOverlayButtons.element,
                props: {
                    state: this.state,
                },
            });
            this.resizeObserver.observe(this.target, { box: "border-box" });
        }
    }

    removeOverlayButtons() {
        if (this.target) {
            this.resizeObserver.unobserve(this.target);
            this.target = null;
        }
        this.overlay.close();
    }

    // TODO improve that (resources ?)
    hasOverlayOptions(el) {
        return isMovable(el) || isResizable(el);
    }
}
