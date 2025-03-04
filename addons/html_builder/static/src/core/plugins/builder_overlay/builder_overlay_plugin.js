import { Plugin } from "@html_editor/plugin";
import { throttleForAnimation } from "@web/core/utils/timing";
import { getScrollingElement, getScrollingTarget } from "@web/core/utils/scrolling";
import { BuilderOverlay, sizingY, sizingX, sizingGrid } from "./builder_overlay";

function isResizable(el) {
    const isResizableY = el.matches(sizingY.selector) && !el.matches(sizingY.exclude);
    const isResizableX = el.matches(sizingX.selector) && !el.matches(sizingX.exclude);
    const isResizableGrid = el.matches(sizingGrid.selector) && !el.matches(sizingGrid.exclude);
    return isResizableY || isResizableX || isResizableGrid;
}

export class BuilderOverlayPlugin extends Plugin {
    static id = "builderOverlay";
    static dependencies = ["localOverlay", "history"];
    static shared = ["showOverlayPreview", "hideOverlayPreview"];
    resources = {
        step_added_handlers: this.refreshOverlays.bind(this),
        change_current_options_containers_listeners: this.openBuilderOverlays.bind(this),
        on_mobile_preview_clicked: this.refreshOverlays.bind(this),
        has_overlay_options: (el) => isResizable(el),
    };

    setup() {
        // TODO find how to not overflow the mobile preview.
        this.iframe = this.editable.ownerDocument.defaultView.frameElement;
        this.overlayContainer = this.dependencies.localOverlay.makeLocalOverlay(
            "builder-overlay-container"
        );
        /** @type {[BuilderOverlay]} */
        this.overlays = [];
        // Refresh the overlays position everytime their target size changes.
        this.resizeObserver = new ResizeObserver(() => this.refreshPositions());

        this._refreshOverlays = throttleForAnimation(this.refreshOverlays.bind(this));

        // Recompute the overlay when the window is resized.
        this.addDomListener(window, "resize", this._refreshOverlays);

        // On keydown, hide the overlay and then show it again when the mouse
        // moves.
        const onMouseMoveOrDown = throttleForAnimation((ev) => {
            this.toggleOverlaysVisibility(true);
            this.refreshPositions();
            ev.currentTarget.removeEventListener("mousemove", onMouseMoveOrDown);
            ev.currentTarget.removeEventListener("mousedown", onMouseMoveOrDown);
        });
        this.addDomListener(this.editable, "keydown", (ev) => {
            this.toggleOverlaysVisibility(false);
            ev.currentTarget.addEventListener("mousemove", onMouseMoveOrDown);
            ev.currentTarget.addEventListener("mousedown", onMouseMoveOrDown);
        });

        // Hide the overlay when scrolling. Show it again when the scroll is
        // over and recompute its position.
        const scrollingElement = getScrollingElement(this.document);
        const scrollingTarget = getScrollingTarget(scrollingElement);
        this.addDomListener(
            scrollingTarget,
            "scroll",
            throttleForAnimation(() => {
                this.toggleOverlaysVisibility(false);
                clearTimeout(this.scrollingTimeout);
                this.scrollingTimeout = setTimeout(() => {
                    this.toggleOverlaysVisibility(true);
                    this.refreshPositions();
                }, 250);
            }),
            { capture: true }
        );

        this._cleanups.push(() => {
            this.removeBuilderOverlays();
            this.resizeObserver.disconnect();
        });
    }

    openBuilderOverlays(optionsContainer) {
        this.removeBuilderOverlays();
        if (!optionsContainer.length) {
            return;
        }

        // Create the overlays.
        optionsContainer.forEach((option) => {
            const overlay = new BuilderOverlay(option.element, {
                iframe: this.iframe,
                overlayContainer: this.overlayContainer,
                addStep: this.dependencies.history.addStep,
                hasOverlayOptions: option.hasOverlayOptions,
            });
            this.overlays.push(overlay);
            this.overlayContainer.append(overlay.overlayElement);
            this.resizeObserver.observe(overlay.overlayTarget, { box: "border-box" });
        });

        // Activate the last overlay.
        const innermostOverlay = this.overlays.at(-1);
        innermostOverlay.toggleOverlay(true);

        // Also activate the closest overlay that should have overlay options.
        if (!innermostOverlay.hasOverlayOptions) {
            for (let i = this.overlays.length - 2; i >= 0; i--) {
                const parentOverlay = this.overlays[i];
                if (parentOverlay.hasOverlayOptions) {
                    parentOverlay.toggleOverlay(true);
                    break;
                }
            }
        }
    }

    removeBuilderOverlays() {
        this.overlays.forEach((overlay) => {
            overlay.destroy();
            overlay.overlayElement.remove();
            this.resizeObserver.unobserve(overlay.overlayTarget);
        });
        this.overlays = [];
    }

    refreshOverlays() {
        this.overlays.forEach((overlay) => {
            overlay.refreshPosition();
            overlay.refreshHandles();
        });
    }

    refreshPositions() {
        this.overlays.forEach((overlay) => {
            overlay.refreshPosition();
        });
    }

    toggleOverlaysVisibility(show) {
        this.overlays.forEach((overlay) => {
            overlay.toggleOverlayVisibility(show);
        });
    }

    showOverlayPreview(el) {
        // Hide all the active overlays.
        this.toggleOverlaysVisibility(false);
        // Show the preview of the one corresponding to the given element.
        const overlayToShow = this.overlays.find((overlay) => overlay.overlayTarget === el);
        // TODO This should actually not be called on mouse event in such cases
        overlayToShow?.toggleOverlayPreview(true);
        overlayToShow?.toggleOverlayVisibility(true);
    }

    hideOverlayPreview(el) {
        // Remove the preview.
        const overlayToHide = this.overlays.find((overlay) => overlay.overlayTarget === el);
        // TODO This should actually not be called on mouse event in such cases
        overlayToHide?.toggleOverlayPreview(false);
        // Show back the active overlays.
        this.toggleOverlaysVisibility(true);
    }
}
