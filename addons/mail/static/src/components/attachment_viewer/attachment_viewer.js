/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { increment } from '@mail/model/model_field_command';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onPatched, onWillUnmount } = owl;

const SCROLL_ZOOM_STEP = 0.1;
const ZOOM_STEP = 0.5;

export class AttachmentViewer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'imageRef', refName: 'image' });
        useRefToModel({ fieldName: 'zoomerRef', refName: 'zoomer' });
        useRefToModel({ fieldName: 'iframeViewerPdfRef', refName: 'iframeViewerPdf' });
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
        this.attachmentViewer.handleImageLoad();
        this.attachmentViewer.hideUnwantedPdfJsButtons();
        document.addEventListener('click', this._onClickGlobal);
    }

    /**
     * When a new image is displayed, show a spinner until it is loaded.
     */
    _patched() {
        this.attachmentViewer.handleImageLoad();
        this.attachmentViewer.hideUnwantedPdfJsButtons();
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
     * Stop dragging interaction of the user.
     *
     * @private
     */
    _stopDragging() {
        this.attachmentViewer.update({ isDragging: false });
        this.attachmentViewer.translate.update({
            dx: 0,
            dy: 0,
            x: increment(this.attachmentViewer.translate.dx),
            y: increment(this.attachmentViewer.translate.dy),
        });
        this.attachmentViewer.updateZoomerStyle();
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
        this.attachmentViewer.updateZoomerStyle();
    }

    /**
     * Zoom out the image.
     *
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.scroll=false]
     */
    _zoomOut({ scroll = false } = {}) {
        if (this.attachmentViewer.scale === this.attachmentViewer.minScale) {
            return;
        }
        const unflooredAdaptedScale = (
            this.attachmentViewer.scale -
            (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP)
        );
        this.attachmentViewer.update({
            scale: Math.max(this.attachmentViewer.minScale, unflooredAdaptedScale),
        });
        this.attachmentViewer.updateZoomerStyle();
    }

    /**
     * Reset the zoom scale of the image.
     *
     * @private
     */
    _zoomReset() {
        this.attachmentViewer.update({ scale: 1 });
        this.attachmentViewer.updateZoomerStyle();
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
        this.attachmentViewer.update({
            isDragging: true,
            dragStartX: ev.clientX,
            dragStartY: ev.clientY,
        });
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
        this.attachmentViewer.translate.update({
            dx: ev.clientX - this.attachmentViewer.dragStartX,
            dy: ev.clientY - this.attachmentViewer.dragStartY,
        });
        this.attachmentViewer.updateZoomerStyle();
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
