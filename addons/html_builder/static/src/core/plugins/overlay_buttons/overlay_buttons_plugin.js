import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { getScrollingElement, getScrollingTarget } from "@web/core/utils/scrolling";
import { OverlayButtons } from "./overlay_buttons";

export class OverlayButtonsPlugin extends Plugin {
    static id = "overlayButtons";
    static dependencies = ["selection", "overlay", "history", "operation"];
    static shared = [
        "hideOverlayButtons",
        "showOverlayButtons",
        "hideOverlayButtonsUi",
        "showOverlayButtonsUi",
    ];
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
                    if (this.target && position.top < iframeRect.top) {
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
            showUi: true,
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
            this.showOverlayButtons();
            ev.currentTarget.removeEventListener("mousemove", onMouseMoveOrDown);
            ev.currentTarget.removeEventListener("mousedown", onMouseMoveOrDown);
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            this.hideOverlayButtons();
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
                this.hideOverlayButtons();
                clearTimeout(this.scrollingTimeout);
                this.scrollingTimeout = setTimeout(() => {
                    this.showOverlayButtons();
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
        for (const button of buttons) {
            const handler = button.handler;
            button.handler = (...args) => {
                this.dependencies.operation.next(async () => {
                    await handler(...args);
                    this.dependencies.history.addStep();
                });
            };
        }
        this.state.buttons = buttons;
        this.overlay.updatePosition();
    }

    hideOverlayButtons() {
        this.state.isVisible = false;
    }

    hideOverlayButtonsUi() {
        this.state.showUi = false;
    }

    showOverlayButtons() {
        this.state.isVisible = true;
    }

    showOverlayButtonsUi() {
        this.state.showUi = true;
    }

    addOverlayButtons(optionsContainer) {
        this.removeOverlayButtons();

        // Find the innermost option needing the overlay buttons.
        const optionWithOverlayButtons = optionsContainer.findLast(
            (option) => option.hasOverlayOptions
        );
        if (optionWithOverlayButtons) {
            this.target = optionWithOverlayButtons.element;
            this.state.isVisible = true;
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
}
