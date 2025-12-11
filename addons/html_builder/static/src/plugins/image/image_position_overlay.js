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

export class ImagePositionOverlay extends Component {
    static template = "html_builder.ImagePositionOverlay";
    static props = {
        targetEl: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        close: { type: Function },
        onDrag: { type: Function },
        getPosition: { type: Function },
        /**
         * `getDelta` should return the difference between the image container
         * dimensions and the image rendered dimensions. Effectively giving the
         * room the image has to move around in each x and y directions.
         */
        getDelta: { type: Function },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        history: Object,
    };

    setup() {
        this.overlayRef = useRef("overlay");
        this.overlayMaskRef = useRef("overlayMask");
        this.overlayContentRef = useRef("overlayContent");
        this.draggerRef = useRef("dragger");

        this.iframeEl = this.props.editable.ownerDocument.defaultView.frameElement;
        this.builderOverlayContainerEl = document.querySelector(
            "[data-oe-local-overlay-id='builder-overlay-container']"
        );

        this._dimensionOverlay = this.dimensionOverlay.bind(this);

        // Discard when clicking anywhere on the page
        const editableDocument = this.props.editable.ownerDocument;
        useExternalListener(editableDocument, "pointerdown", this.discard.bind(this));
        useExternalListener(document, "pointerdown", this.discard.bind(this));

        useExternalListener(window, "resize", this._dimensionOverlay);
        useExternalListener(this.iframeEl.contentWindow, "resize", this._dimensionOverlay);
        useExternalListener(this.iframeEl.contentWindow, "scroll", this._dimensionOverlay);

        onWillStart(async () => {
            const position = this.props
                .getPosition()
                .split(" ")
                .map((v) => parseInt(v));
            const delta = this.props.getDelta();
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
            const rect = this.props.targetEl.getBoundingClientRect();
            const isEditingElEntirelyVisible =
                rect.top >= 0 &&
                rect.bottom <= this.props.targetEl.ownerDocument.defaultView.innerHeight;
            if (!isEditingElEntirelyVisible) {
                await scrollTo(this.props.targetEl, { extraOffset: 50 });
            }
        });

        onMounted(() => {
            this.reloadSavePoint = this.props.history.makeSavePoint();
            this.dimensionOverlay();
            this.props.targetEl.classList.add("o_we_image_positioning");
        });

        useEffect(() => {
            this.tooltip = window.Tooltip.getOrCreateInstance(this.draggerRef.el, {
                trigger: "manual",
                container: this.overlayRef.el,
            });
            this.tooltip.show();
        });

        onWillUnmount(() => {
            this.builderOverlayContainerEl.style.clipPath = "";
            this.tooltip.dispose();
        });
    }

    apply() {
        const position = this.props.getPosition();
        this.reloadSavePoint();
        this.props.close(position);
    }

    discard() {
        this.reloadSavePoint();
        this.props.close(null);
    }

    onWheel(ev) {
        if (ev.ctrlKey) {
            return;
        }
        this.iframeEl.contentWindow.scrollBy(ev.deltaX, ev.deltaY);
    }

    onDragStart() {
        this.overlayRef.el.classList.add("o_we_grabbing");
        const documentEl = window.document;
        const onDragMove = this.onDragMove.bind(this);
        documentEl.addEventListener("mousemove", onDragMove);
        documentEl.addEventListener(
            "mouseup",
            () => {
                this.overlayRef.el.classList.remove("o_we_grabbing");
                documentEl.removeEventListener("mousemove", onDragMove);
            },
            { once: true }
        );
    }

    /**
     * Drags the overlay's image.
     */
    onDragMove(ev) {
        ev.preventDefault();

        const delta = this.props.getDelta();
        const clamp = (val, bounds) => {
            // We sort the bounds because delta.x or delta.y can be negative.
            bounds = bounds.sort();
            return Math.max(bounds[0], Math.min(val, bounds[1]));
        };
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

        this.props.onDrag(percentPosition);
    }

    dimensionOverlay() {
        const iframeRect = this.iframeEl.getBoundingClientRect();
        const targetContainerRect = this.props.targetEl.getBoundingClientRect();
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
        Object.assign(this.overlayRef.el.style, {
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
        this.draggerRef.el.style.setProperty("width", `${scaledRect.width}px`, "important");
        this.draggerRef.el.style.setProperty("height", `${scaledRect.height}px`, "important");

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
        const matrix = getComputedStyle(this.iframeEl.parentElement).transform;
        if (matrix === "none") {
            return 1;
        }
        const values = matrix
            .match(/matrix\(([^)]+)\)/)[1]
            .split(",")
            .map(parseFloat);
        return values[0];
    }
}
