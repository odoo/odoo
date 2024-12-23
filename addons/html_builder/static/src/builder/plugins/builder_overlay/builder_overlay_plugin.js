import { Plugin } from "@html_editor/plugin";
import { throttleForAnimation } from "@web/core/utils/timing";
import { getScrollingElement, getScrollingTarget } from "@web/core/utils/scrolling";
import { BuilderOverlay } from "./builder_overlay";

export class BuilderOverlayPlugin extends Plugin {
    static id = "builderOverlay";
    static dependencies = ["selection", "localOverlay", "history"];
    resources = {
        step_added_handlers: this._update.bind(this),
        change_current_options_containers_listeners: this.openBuilderOverlay.bind(this),
        on_mobile_preview_clicked: this._update.bind(this),
    };

    setup() {
        // TODO find how to not overflow the mobile preview.
        this.iframe = this.editable.ownerDocument.defaultView.frameElement;
        this.overlayContainer = this.dependencies.localOverlay.makeLocalOverlay(
            "builder-overlay-container"
        );
        /** @type {[BuilderOverlay]} */
        this.overlays = [];

        this.update = throttleForAnimation(this._update.bind(this));

        // Recompute the overlay when the window is resized.
        this.addDomListener(window, "resize", this.update);

        // On keydown, hide the overlay and then show it again when the mouse
        // moves.
        const onMouseMoveOrDown = throttleForAnimation((ev) => {
            this.toggleOverlaysVisibility(true);
            this.refreshPosition();
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
                    this.refreshPosition();
                }, 250);
            }),
            { capture: true }
        );

        this._cleanups.push(() => this.removeBuilderOverlay());
    }

    openBuilderOverlay(optionsContainer) {
        this.removeBuilderOverlay();
        if (!optionsContainer.length) {
            return;
        }

        // Create the overlays.
        optionsContainer.forEach((option) => {
            const overlay = new BuilderOverlay(option.element, {
                iframe: this.iframe,
                overlayContainer: this.overlayContainer,
                addStep: this.dependencies.history.addStep,
                refreshAllOverlaysPosition: this.refreshPosition.bind(this),
            });
            this.overlays.push(overlay);
            this.overlayContainer.append(overlay.overlayElement);
        });

        // Activate the last overlay.
        const innermostOverlay = this.overlays.at(-1);
        innermostOverlay.toggleOverlay(true);

        // Also activate the closest overlay that should have sizing
        // handles.
        if (!innermostOverlay.hasSizingHandles) {
            for (let i = this.overlays.length - 2; i >= 0; i--) {
                const parentOverlay = this.overlays[i];
                if (parentOverlay.hasSizingHandles) {
                    parentOverlay.toggleOverlay(true);
                    break;
                }
            }
        }

        // TODO check if resizeObserver still needed.
        // this.resizeObserver = new ResizeObserver(this.update.bind(this));
        // this.resizeObserver.observe(this.overlayTarget);
    }

    removeBuilderOverlay() {
        this.overlays.forEach((overlay) => {
            overlay.destroy();
            overlay.overlayElement.remove();
        });
        this.overlays = [];
        // this.resizeObserver?.disconnect();
    }

    _update() {
        this.overlays.forEach((overlay) => {
            overlay.refreshPosition();
            overlay.refreshHandles();
        });
    }

    refreshPosition() {
        this.overlays.forEach((overlay) => {
            overlay.refreshPosition();
        });
    }

    refreshHandles() {
        this.overlays.forEach((overlay) => {
            overlay.refreshHandles();
        });
    }

    toggleOverlaysVisibility(show) {
        this.overlays.forEach((overlay) => {
            overlay.toggleOverlayVisibility(show);
        });
    }
}
