import { scrollTo } from "@html_builder/utils/scrolling";
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useEffect,
    useExternalListener,
    useRef,
} from "@odoo/owl";

export class BackgroundPositionOverlay extends Component {
    static template = "html_builder.BackgroundPositionOverlay";
    static props = {
        editingElement: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        mockEditingElOnImg: { validate: (p) => p.tagName === "IMG" },
        applyPosition: { type: Function },
        discardPosition: { type: Function },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        history: Object,
    };

    setup() {
        this.backgroundOverlayRef = useRef("backgroundOverlay");
        this.overlayMaskRef = useRef("overlayMask");
        this.overlayContentRef = useRef("overlayContent");
        this.bgDraggerRef = useRef("bgDragger");

        this.iframe = this.props.editable.ownerDocument.defaultView.frameElement;
        this.builderOverlayContainerEl = document.querySelector(
            "[data-oe-local-overlay-id='builder-overlay-container']:not(:empty)"
        );
        // If there is a Scroll Effect, a span.s_parallax_bg inside the section
        // contains the background. Otherwise it's the section itself.
        // And targetContainerEl should always be the section.
        this.targetContainerEl = this.props.editingElement.classList.contains("s_parallax_bg")
            ? this.props.editingElement.parentElement
            : this.props.editingElement;

        this._dimensionOverlay = this.dimensionOverlay.bind(this);

        // Discard when clicking anywhere on the page
        const editableDocument = this.props.editable.ownerDocument;
        useExternalListener(editableDocument, "pointerdown", this.discard.bind(this));
        useExternalListener(document, "pointerdown", this.discard.bind(this));

        useExternalListener(window, "resize", this._dimensionOverlay);
        useExternalListener(this.iframe.contentWindow, "resize", this._dimensionOverlay);
        useExternalListener(this.iframe.contentWindow, "scroll", this._dimensionOverlay);

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
            const rect = this.targetContainerEl.getBoundingClientRect();
            const isEditingElEntirelyVisible =
                rect.top >= 0 &&
                rect.bottom <= this.targetContainerEl.ownerDocument.defaultView.innerHeight;
            if (!isEditingElEntirelyVisible) {
                await scrollTo(this.targetContainerEl, { extraOffset: 50 });
            }
        });

        onMounted(() => {
            this.reloadSavePoint = this.props.history.makeSavePoint();
            this.dimensionOverlay();
            this.targetContainerEl.classList.add("o_we_background_positioning");
        });

        useEffect(() => {
            this.tooltip = window.Tooltip.getOrCreateInstance(this.bgDraggerRef.el, {
                trigger: "manual",
                container: this.backgroundOverlayRef.el,
            });
            this.tooltip.show();
        });

        onWillUnmount(() => {
            this.builderOverlayContainerEl.style.clipPath = "";
            this.tooltip.dispose();
        });
    }

    apply() {
        const position = getComputedStyle(this.props.editingElement).backgroundPosition;
        this.reloadSavePoint();
        this.props.applyPosition(position);
    }

    discard() {
        this.reloadSavePoint();
        this.props.discardPosition();
    }

    onWheel(ev) {
        if (ev.ctrlKey) {
            return;
        }
        this.iframe.contentWindow.scrollBy(ev.deltaX, ev.deltaY);
    }

    onDragBackgroundStart(ev) {
        this.backgroundOverlayRef.el.classList.add("o_we_grabbing");
        const documentEl = window.document;
        const onDragBackgroundMove = this.onDragBackgroundMove.bind(this);
        documentEl.addEventListener("mousemove", onDragBackgroundMove);
        documentEl.addEventListener(
            "mouseup",
            () => {
                this.backgroundOverlayRef.el.classList.remove("o_we_grabbing");
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

        this.props.editingElement.style.backgroundPosition = `${percentPosition.left}% ${percentPosition.top}%`;

        function clamp(val, bounds) {
            // We sort the bounds because when one dimension of the rendered
            // background is larger than the container, delta is negative, and
            // we want to use it as lower bound.
            bounds = bounds.sort();
            return Math.max(bounds[0], Math.min(val, bounds[1]));
        }
    }

    dimensionOverlay() {
        const iframeRect = this.iframe.getBoundingClientRect();
        const targetContainerRect = this.targetContainerEl.getBoundingClientRect();
        const scale = this.getIframeContainerScale();
        const scaledRect = new DOMRect(
            scale * targetContainerRect.x,
            scale * targetContainerRect.y,
            scale * targetContainerRect.width,
            scale * targetContainerRect.height
        );

        // Make a cut-out in the overlay mask to highlight the editing element.
        // "polygon" is used because "rect" would do the inverse.
        const clipPath = `polygon(
            evenodd,
            0 0, 100% 0,100% 100%, 0 100%, 0 0,
            ${scaledRect.left}px ${scaledRect.top}px,
            ${scaledRect.right}px ${scaledRect.top}px,
            ${scaledRect.right}px ${scaledRect.bottom}px,
            ${scaledRect.left}px ${scaledRect.bottom}px,
            ${scaledRect.left}px ${scaledRect.top}px)
        `;
        this.overlayMaskRef.el.style.clipPath = clipPath;
        this.builderOverlayContainerEl.style.clipPath = clipPath;

        // The overlay covers the whole iframe excluding the scrollbar.
        Object.assign(this.backgroundOverlayRef.el.style, {
            left: `${iframeRect.left}px`,
            top: `${iframeRect.top}px`,
            height: `${this.props.editable.ownerDocument.body.clientHeight * scale}px`,
            width: `${this.props.editable.ownerDocument.body.clientWidth * scale}px`,
        });

        // The overlay content covers the editing element.
        Object.assign(this.overlayContentRef.el.style, {
            left: `${scaledRect.left}px`,
            top: `${scaledRect.top}px`,
        });
        const overlayButtonsEl = this.overlayContentRef.el.querySelector(".o_we_overlay_buttons");
        overlayButtonsEl.style.top = `${Math.max(0, -scaledRect.top)}px`;
        this.bgDraggerRef.el.style.setProperty("width", `${scaledRect.width}px`, "important");
        this.bgDraggerRef.el.style.setProperty("height", `${scaledRect.height}px`, "important");

        // Refresh tooltip position after overlay reposition
        if (this.tooltip) {
            this.tooltip.update();
        }
    }

    /**
     * Gets the scale factor of the iframe's parent container.
     * Useful when the user zooms in/out in the browser, as it affects the
     * dimensions of the iframe.
     * @returns {number} The scale factor (1 if no transform is applied)
     */
    getIframeContainerScale() {
        const matrix = getComputedStyle(this.iframe.parentElement).transform;
        if (matrix === "none") {
            return 1;
        }
        const values = matrix
            .match(/matrix\(([^)]+)\)/)[1]
            .split(",")
            .map(parseFloat);
        return values[0];
    }

    /**
     * Returns the difference between the editing element's size and the
     * background's rendered size. Background position values in % are a
     * percentage of this.
     *
     */
    getBackgroundDelta() {
        const naturalWidth = this.props.mockEditingElOnImg.naturalWidth;
        const naturalHeight = this.props.mockEditingElOnImg.naturalHeight;
        const editingElStyle = getComputedStyle(this.props.editingElement);
        // If background-attachment: fixed, the background is sized relative to
        // the page viewport.
        const bgRect =
            editingElStyle.backgroundAttachment === "fixed"
                ? this.iframe.getBoundingClientRect()
                : this.props.editingElement.getBoundingClientRect();

        if (editingElStyle.backgroundSize === "cover") {
            const renderRatio = Math.max(
                bgRect.width / naturalWidth,
                bgRect.height / naturalHeight
            );

            return {
                x: bgRect.width - Math.round(renderRatio * naturalWidth),
                y: bgRect.height - Math.round(renderRatio * naturalHeight),
            };
        }

        let [width, height] = editingElStyle.backgroundSize.split(" ");
        if (width === "auto" && (height === "auto" || !height)) {
            return {
                x: bgRect.width - naturalWidth,
                y: bgRect.height - naturalHeight,
            };
        }
        // At least one of width or height is not auto, so we can use it to
        // calculate the other if it's not set.
        [width, height] = [parseInt(width), parseInt(height)];
        return {
            x: bgRect.width - (width || (height * naturalWidth) / naturalHeight),
            y: bgRect.height - (height || (width * naturalHeight) / naturalWidth),
        };
    }
}
