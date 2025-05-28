import { scrollTo } from "@html_builder/utils/scrolling";
import { Component, onMounted, onWillStart, onWillUnmount, useEffect, useRef } from "@odoo/owl";

export class BackgroundPositionOverlay extends Component {
    static template = "website.BackgroundPositionOverlay";
    static props = {
        outerHtmlEditingElement: { type: String },
        editingElement: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        mockEditingElOnImg: { validate: (p) => p.tagName === "IMG" },
        applyPosition: { type: Function },
        discardPosition: { type: Function },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
    };
    setup() {
        this.parentBgDragger = useRef("parentBgDragger");
        this.backgroundOverlay = useRef("backgroundOverlay");
        this.overlayContent = useRef("overlayContent");
        // This has been put here as it is used in an event listener. As we need
        // to remove the event listener and the method needs to access the
        // `BgPositionOverlay` instance, it has to be an array function.
        this.dimensionOverlay = () => {
            // Sets the overlay in the right place so that the draggable
            // background sizes the background item like the editing element.
            this.backgroundOverlay.el.style.width = `${this.props.editable.clientWidth}px`;
            this.backgroundOverlay.el.style.height = `${this.props.editable.clientHeight}px`;
            const overlayContentEl = this.overlayContent.el;

            this.bgDraggerEl.style.width = `${this.props.editingElement.clientWidth}px`;
            this.bgDraggerEl.style.height = `${this.props.editingElement.clientHeight}px`;

            const topPos = Math.max(
                0,
                window.scrollY -
                    (this.props.editingElement.getBoundingClientRect().top + window.scrollY)
            );
            overlayContentEl.querySelector(".o_we_overlay_buttons").style.top = `${topPos}px`;
        };
        onWillStart(async () => {
            const position = getComputedStyle(this.props.editingElement)
                .backgroundPosition.split(" ")
                .map((v) => parseInt(v));
            const delta = this.getBackgroundDelta();
            // originalPosition kept in % for when movement in one direction
            // doesn't make sense.
            this.originalPosition = { left: position[0], top: position[1] };
            // Convert % values to pixels for current position because
            // mouse movement is in pixels.
            this.currentPosition = {
                left: (position[0] / 100) * delta.x || 0,
                top: (position[1] / 100) * delta.y || 0,
            };
            // Make sure the editing element is visible
            // TODO: check; the overlay could fail to be visible if the editing
            // element is too big.
            const rect = this.props.editingElement.getBoundingClientRect();
            const isEditingElEntirelyVisible =
                rect.top >= 0 &&
                rect.bottom <= this.props.editingElement.ownerDocument.defaultView.innerHeight;
            if (!isEditingElEntirelyVisible) {
                await scrollTo(this.props.editingElement, { extraOffset: 50 });
            }
        });
        onMounted(() => {
            this.bgDraggerEl = this.parentBgDragger.el.children[0];
            this.dimensionOverlay();
            this.bgDraggerEl.style.backgroundAttachment = getComputedStyle(
                this.props.editingElement
            ).backgroundAttachment;
            window.addEventListener("resize", this.dimensionOverlay);
        });
        useEffect(() => {
            this.tooltip = window.Tooltip.getOrCreateInstance(this.parentBgDragger.el, {
                trigger: "manual",
                container: this.backgroundOverlay.el,
            });
            this.tooltip.show();
        });
        onWillUnmount(() => {
            window.removeEventListener("resize", this.dimensionOverlay);
            this.tooltip.dispose();
        });
    }
    apply() {
        this.props.applyPosition(getComputedStyle(this.bgDraggerEl).backgroundPosition);
    }
    onDragBackgroundStart(ev) {
        this.bgDraggerEl.classList.add("o_we_grabbing");
        const documentEl = window.document;
        const onDragBackgroundMove = this.onDragBackgroundMove.bind(this);
        documentEl.addEventListener("mousemove", onDragBackgroundMove);
        documentEl.addEventListener(
            "mouseup",
            () => {
                this.bgDraggerEl.classList.remove("o_we_grabbing");
                documentEl.removeEventListener("mousemove", onDragBackgroundMove);
            },
            { once: true }
        );
    }
    /**
     * Drags the overlay's background image.
     *
     */
    onDragBackgroundMove(ev) {
        ev.preventDefault();

        const delta = this.getBackgroundDelta();
        this.currentPosition.left = clamp(this.currentPosition.left + ev.movementX, [0, delta.x]);
        this.currentPosition.top = clamp(this.currentPosition.top + ev.movementY, [0, delta.y]);

        const percentPosition = {
            left: (this.currentPosition.left / delta.x) * 100,
            top: (this.currentPosition.top / delta.y) * 100,
        };
        // In cover mode, one delta will be 0 and dividing by it will yield
        // Infinity. Defaulting to originalPosition in that case (can't be
        // dragged).
        percentPosition.left = isFinite(percentPosition.left)
            ? percentPosition.left
            : this.originalPosition.left;
        percentPosition.top = isFinite(percentPosition.top)
            ? percentPosition.top
            : this.originalPosition.top;

        this.bgDraggerEl.style.backgroundPosition = `${percentPosition.left}% ${percentPosition.top}%`;

        function clamp(val, bounds) {
            // We sort the bounds because when one dimension of the rendered
            // background is larger than the container, delta is negative, and
            // we want to use it as lower bound.
            bounds = bounds.sort();
            return Math.max(bounds[0], Math.min(val, bounds[1]));
        }
    }
    /**
     * Returns the difference between the editing element's size and the
     * background's rendered size. Background position values in % are a
     * percentage of this.
     *
     */
    getBackgroundDelta() {
        const bgSize = getComputedStyle(this.props.editingElement).backgroundSize;
        const editingElDimension = this.props.editingElement.getBoundingClientRect();
        if (bgSize !== "cover") {
            let [width, height] = bgSize.split(" ");
            if (width === "auto" && (height === "auto" || !height)) {
                return {
                    x: editingElDimension.width - this.props.mockEditingElOnImg.naturalWidth,
                    y: editingElDimension.height - this.props.mockEditingElOnImg.naturalHeight,
                };
            }
            // At least one of width or height is not auto, so we can use it to
            // calculate the other if it's not set.
            [width, height] = [parseInt(width), parseInt(height)];
            return {
                x:
                    editingElDimension.width -
                    (width ||
                        (height * this.props.mockEditingElOnImg.naturalWidth) /
                            this.props.mockEditingElOnImg.naturalHeight),
                y:
                    editingElDimension.height -
                    (height ||
                        (width * this.props.mockEditingElOnImg.naturalHeight) /
                            this.props.mockEditingElOnImg.naturalWidth),
            };
        }

        const renderRatio = Math.max(
            editingElDimension.width / this.props.mockEditingElOnImg.naturalWidth,
            editingElDimension.height / this.props.mockEditingElOnImg.naturalHeight
        );

        return {
            x:
                editingElDimension.width -
                Math.round(renderRatio * this.props.mockEditingElOnImg.naturalWidth),
            y:
                editingElDimension.height -
                Math.round(renderRatio * this.props.mockEditingElOnImg.naturalHeight),
        };
    }
}
