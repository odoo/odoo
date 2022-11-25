/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefs } from '@mail/component_hooks/use_refs';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { hidePDFJSButtons } from '@web/legacy/js/libs/pdfjs';

const { Component, onMounted, onPatched, onWillUnmount, useRef } = owl;

const MIN_SCALE = 0.5;
const SCROLL_ZOOM_STEP = 0.1;
const ZOOM_STEP = 0.5;

export class AttachmentViewer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        this.MIN_SCALE = MIN_SCALE;
        /**
         * Used to ensure that the ref is always up to date, which seems to be needed if the element
         * has a t-key, which was added to force the rendering of a new element when the src of the image changes.
         * This was made to remove the display of the previous image as soon as the src changes.
         */
        this._getRefs = useRefs();
        /**
         * Reference of the zoomer node. Useful to apply translate
         * transformation on image visualisation.
         */
        this._zoomerRef = useRef('zoomer');
        /**
         * Reference of the IFRAME node when the attachment is a PDF.
         */
        this._iframeViewerPdfRef = useRef('iframeViewerPdf');
        /**
         * Tracked translate transformations on image visualisation. This is
         * not observed for re-rendering because they are used to compute zoomer
         * style, and this is changed directly on zoomer for performance
         * reasons (overhead of making vdom is too significant for each mouse
         * position changes while dragging)
         */
        this._translate = { x: 0, y: 0, dx: 0, dy: 0 };
        this._onClickGlobal = this._onClickGlobal.bind(this);
        onMounted(() => this._mounted());
        onPatched(() => this._patched());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        if (!this.root.el) {
            return;
        }
        this.root.el.focus();
        this._handleImageLoad();
        this._hideUnwantedPdfJsButtons();
        document.addEventListener('click', this._onClickGlobal);
    }

    /**
     * When a new image is displayed, show a spinner until it is loaded.
     */
    _patched() {
        this._handleImageLoad();
        this._hideUnwantedPdfJsButtons();
    }

    _willUnmount() {
        document.removeEventListener('click', this._onClickGlobal);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentViewer}
     */
    get attachmentViewer() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Determine whether the current image is rendered for the 1st time, and if
     * that's the case, display a spinner until loaded.
     *
     * @private
     */
    _handleImageLoad() {
        if (!this.attachmentViewer.exists() || !this.attachmentViewer.attachmentViewerViewable) {
            return;
        }
        const refs = this._getRefs();
        const image = refs[`image_${this.attachmentViewer.attachmentViewerViewable.localId}`];
        if (
            this.attachmentViewer.attachmentViewerViewable.isImage &&
            (!image || !image.complete)
        ) {
            this.attachmentViewer.update({ isImageLoading: true });
        }
    }

    /**
     * @see 'hidePDFJSButtons'
     *
     * @private
     */
    _hideUnwantedPdfJsButtons() {
        if (this._iframeViewerPdfRef.el) {
            hidePDFJSButtons(this._iframeViewerPdfRef.el);
        }
    }

    /**
     * Stop dragging interaction of the user.
     *
     * @private
     */
    _stopDragging() {
        this.attachmentViewer.update({ isDragging: false });
        this._translate.x += this._translate.dx;
        this._translate.y += this._translate.dy;
        this._translate.dx = 0;
        this._translate.dy = 0;
        this._updateZoomerStyle();
    }

    /**
     * Update the style of the zoomer based on translate transformation. Changes
     * are directly applied on zoomer, instead of triggering re-render and
     * defining them in the template, for performance reasons.
     *
     * @private
     * @returns {string}
     */
    _updateZoomerStyle() {
        const attachmentViewer = this.attachmentViewer;
        const refs = this._getRefs();
        const image = refs[`image_${this.attachmentViewer.attachmentViewerViewable.localId}`];
        // some actions are too fast that sometimes this function is called
        // before setting the refs, so we just do nothing when image is null
        if (!image) {
            return;
        }
        const tx = image.offsetWidth * attachmentViewer.scale > this._zoomerRef.el.offsetWidth
            ? this._translate.x + this._translate.dx
            : 0;
        const ty = image.offsetHeight * attachmentViewer.scale > this._zoomerRef.el.offsetHeight
            ? this._translate.y + this._translate.dy
            : 0;
        if (tx === 0) {
            this._translate.x = 0;
        }
        if (ty === 0) {
            this._translate.y = 0;
        }
        this._zoomerRef.el.style = `transform: ` +
            `translate(${tx}px, ${ty}px)`;
    }

    /**
     * Zoom in the image.
     *
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.scroll=false]
     */
    _zoomIn({ scroll = false } = {}) {
        this.attachmentViewer.update({
            scale: this.attachmentViewer.scale + (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP),
        });
        this._updateZoomerStyle();
    }

    /**
     * Zoom out the image.
     *
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.scroll=false]
     */
    _zoomOut({ scroll = false } = {}) {
        if (this.attachmentViewer.scale === MIN_SCALE) {
            return;
        }
        const unflooredAdaptedScale = (
            this.attachmentViewer.scale -
            (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP)
        );
        this.attachmentViewer.update({
            scale: Math.max(MIN_SCALE, unflooredAdaptedScale),
        });
        this._updateZoomerStyle();
    }

    /**
     * Reset the zoom scale of the image.
     *
     * @private
     */
    _zoomReset() {
        this.attachmentViewer.update({ scale: 1 });
        this._updateZoomerStyle();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGlobal(ev) {
        if (!this.attachmentViewer.exists()) {
            return;
        }
        if (!this.attachmentViewer.isDragging) {
            return;
        }
        ev.stopPropagation();
        this._stopDragging();
    }

    /**
     * Called when clicking on zoom in icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomIn(ev) {
        ev.stopPropagation();
        this._zoomIn();
    }

    /**
     * Called when clicking on zoom out icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomOut(ev) {
        ev.stopPropagation();
        this._zoomOut();
    }

    /**
     * Called when clicking on reset zoom icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomReset(ev) {
        ev.stopPropagation();
        this._zoomReset();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        switch (ev.key) {
            case 'ArrowRight':
                this.attachmentViewer.next();
                break;
            case 'ArrowLeft':
                this.attachmentViewer.previous();
                break;
            case 'Escape':
                this.attachmentViewer.close();
                break;
            case 'q':
                this.attachmentViewer.close();
                break;
            case 'r':
                this.attachmentViewer.rotate();
                break;
            case '+':
                this._zoomIn();
                break;
            case '-':
                this._zoomOut();
                break;
            case '0':
                this._zoomReset();
                break;
            default:
                return;
        }
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {DragEvent} ev
     */
    _onMousedownImage(ev) {
        if (!this.attachmentViewer.exists()) {
            return;
        }
        if (this.attachmentViewer.isDragging) {
            return;
        }
        if (ev.button !== 0) {
            return;
        }
        ev.stopPropagation();
        this.attachmentViewer.update({ isDragging: true });
        this._dragstartX = ev.clientX;
        this._dragstartY = ev.clientY;
    }

    /**
     * @private
     * @param {DragEvent}
     */
    _onMousemoveView(ev) {
        if (!this.attachmentViewer.exists()) {
            return;
        }
        if (!this.attachmentViewer.isDragging) {
            return;
        }
        this._translate.dx = ev.clientX - this._dragstartX;
        this._translate.dy = ev.clientY - this._dragstartY;
        this._updateZoomerStyle();
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onWheelImage(ev) {
        ev.stopPropagation();
        if (!this.root.el) {
            return;
        }
        if (ev.deltaY > 0) {
            this._zoomOut({ scroll: true });
        } else {
            this._zoomIn({ scroll: true });
        }
    }

}

Object.assign(AttachmentViewer, {
    props: { record: Object },
    template: 'mail.AttachmentViewer',
});

registerMessagingComponent(AttachmentViewer);
