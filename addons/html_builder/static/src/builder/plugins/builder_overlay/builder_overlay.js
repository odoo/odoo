import { renderToElement } from "@web/core/utils/render";
import { isMobileView } from "@html_builder/builder/utils/utils";

const sizingY = {
    selector: "section, .row > div, .parallax, .s_hr, .carousel-item, .s_rating",
    exclude:
        "section:has(> .carousel), .s_image_gallery .carousel-item, .s_col_no_resize.row > div, .s_col_no_resize",
};
const sizingX = {
    selector: ".row > div",
    exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
};
const sizingGrid = {
    selector: ".row > div",
    exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
};

export class BuilderOverlay {
    constructor(overlayTarget, { overlayContainer }) {
        this.overlayContainer = overlayContainer;
        this.overlayElement = renderToElement("html_builder.BuilderOverlay");
        this.overlayTarget = overlayTarget;
        this.hasSizingHandles = this.hasSizingHandles();
        this.handlesWrapperEl = this.overlayElement.querySelector(".o_handles");
        this.handleEls = this.overlayElement.querySelectorAll(".o_handle");
    }

    hasSizingHandles() {
        return (
            this.overlayTarget.matches(`${sizingY.selector}:not(${sizingY.exclude})`) ||
            this.overlayTarget.matches(`${sizingX.selector}:not(${sizingX.exclude})`) ||
            this.overlayTarget.matches(`${sizingGrid.selector}:not(${sizingGrid.exclude})`)
        );
    }

    // displayOverlayOptions(el) {
    //     // TODO when options will be more clear:
    //     // - moving
    //     // - timeline
    //     // (maybe other where `displayOverlayOptions: true`)
    // }

    isActive() {
        // TODO active still necessary ? (check when we have preview mode)
        return this.overlayElement.classList.contains("oe_active");
    }

    refreshPosition() {
        if (!this.isActive()) {
            return;
        }

        // TODO transform
        const overlayContainerRect = this.overlayContainer.getBoundingClientRect();
        const targetRect = this.overlayTarget.getBoundingClientRect();
        Object.assign(this.overlayElement.style, {
            width: `${targetRect.width}px`,
            height: `${targetRect.height}px`,
            top: `${targetRect.y - overlayContainerRect.y + window.scrollY}px`,
            left: `${targetRect.x - overlayContainerRect.x + window.scrollX}px`,
        });
        this.handlesWrapperEl.style.height = `${targetRect.height}px`;
    }

    refreshHandles() {
        if (!this.hasSizingHandles || !this.isActive()) {
            return;
        }

        if (this.overlayTarget.parentNode?.classList.contains("row")) {
            const isMobile = isMobileView(this.overlayTarget);
            const isGridOn = this.overlayTarget.classList.contains("o_grid_item");
            const isGrid = !isMobile && isGridOn;
            // Hiding/showing the correct resize handles if we are in grid mode
            // or not.
            this.handleEls.forEach((handleEl) => {
                const isGridHandle = handleEl.classList.contains("o_grid_handle");
                handleEl.classList.toggle("d-none", isGrid ^ isGridHandle);
                // Disabling the vertical resize if we are in mobile view.
                const isVerticalSizing = handleEl.matches(".n, .s");
                handleEl.classList.toggle("readonly", isMobile && isVerticalSizing && isGridOn);
            });
        }
    }

    toggleOverlay(show) {
        this.overlayElement.classList.add("oe_active", show);
        this.refreshPosition();
        this.refreshHandles();
    }

    toggleOverlayVisibility(show) {
        if (!this.isActive()) {
            return;
        }
        this.overlayElement.classList.toggle("o_overlay_hidden", !show);
    }
}
