odoo.define('mail.component.AttachmentViewer', function () {
'use strict';

const { Component, QWeb, useState } = owl;
const { useDispatch, useGetters, useRef, useStore } = owl.hooks;

const MIN_SCALE = 0.5;
const SCROLL_ZOOM_STEP = 0.1;
const ZOOM_STEP = 0.5;

class AttachmentViewer extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.MIN_SCALE = MIN_SCALE;
        this.state = useState({
            /**
             * Angle of the image. Changes when the user rotates it.
             */
            angle: 0,
            /**
             * Determine whether the image is loading or not. Useful to diplay
             * a spinner when loading image initially.
             */
            isImageLoading: false,
            /**
             * Scale size of the image. Changes when user zooms in/out.
             */
            scale: 1,
        });
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            return {
                attachment: state.attachments[props.info.attachmentLocalId],
            };
        });
        /**
         * Determine whether the user is currently dragging the image.
         * This is useful to determine whether a click outside of the image
         * should close the attachment viewer or not.
         */
        this._isDragging = false;
        /**
         * Reference to the image node. Useful in the computation of the zoomer
         * style (based on user zoom in/out interactions).
         */
        this._imageRef = useRef('image');
        /**
         * Reference of the zoomer node. Useful to apply translate
         * transformation on image visualisation.
         */
        this._zoomerRef = useRef('zoomer');
        /**
         * Tracked translate transformations on image visualisation. This is
         * not observed with `useState` because they are used to compute zoomer
         * style, and this is changed directly on zoomer for performance
         * reasons (overhead of making vdom is too significant for each mouse
         * position changes while dragging)
         */
        this._translate = { x: 0, y: 0, dx: 0, dy: 0 };
        /**
         * Tracked last rendered attachment. Useful to detect a new image is
         * loading, in order to display spinner until it is fully loaded.
         */
        this._renderedAttachmentLocalId = undefined;
        this._onClickGlobal = this._onClickGlobal.bind(this);
    }

    mounted() {
        this.el.focus();
        this._handleImageLoad();
        this._renderedAttachmentLocalId = this.props.info.attachmentLocalId;
        document.addEventListener('click', this._onClickGlobal);
    }

    /**
     * When a new image is displayed, show a spinner until it is loaded.
     */
    patched() {
        this._handleImageLoad();
        this._renderedAttachmentLocalId = this.props.info.attachmentLocalId;
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickGlobal);
    }

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    /**
     * Compute the style of the image (scale + rotation).
     *
     * @return {string}
     */
    get imageStyle() {
        let style = `transform: ` +
            `scale3d(${this.state.scale}, ${this.state.scale}, 1) ` +
            `rotate(${this.state.angle}deg);`;

        if (this.state.angle % 180 !== 0) {
            style += `` +
                `max-height: ${window.innerWidth}px; ` +
                `max-width: ${window.innerHeight}px;`;
        } else {
            style += `` +
                `max-height: 100%; ` +
                `max-width: 100%;`;
        }
        return style;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Mandatory method for dialog components.
     * Prevent closing the dialog when clicking on the mask when the user is
     * currently dragging the image.
     *
     * @return {boolean}
     */
    isCloseable() {
        return !this._isDragging;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Close the dialog with this attachment viewer.
     *
     * @private
     */
    _close() {
        this.storeDispatch('closeDialog', this.props.id);
    }

    /**
     * Download the attachment.
     *
     * @private
     */
    _download() {
        window.location = `/web/content/ir.attachment/${this.storeProps.attachment.id}/datas?download=true`;
    }

    /**
     * Determine whether the current image is rendered for the 1st time, and if
     * that's the case, display a spinner until loaded.
     *
     * @private
     */
    _handleImageLoad() {
        if (
            this.storeGetters.attachmentFileType(this.props.info.attachmentLocalId) === 'image' &&
            this._renderedAttachmentLocalId !== this.props.info.attachmentLocalId
        ) {
            this.state.isImageLoading = true;
            this._imageRef.el.addEventListener('load', ev => this._onLoadImage(ev));
        }
    }

    /**
     * Display the previous attachment in the list of attachments.
     *
     * @private
     */
    _next() {
        const index = this.props.info.attachmentLocalIds.findIndex(localId =>
            localId === this.props.info.attachmentLocalId);
        const nextIndex = (index + 1) % this.props.info.attachmentLocalIds.length;
        this.storeDispatch('updateDialogInfo', this.props.dialogId, {
            attachmentLocalId: this.props.info.attachmentLocalIds[nextIndex],
        });
    }

    /**
     * Display the previous attachment in the list of attachments.
     *
     * @private
     */
    _previous() {
        const index = this.props.info.attachmentLocalIds.findIndex(localId =>
            localId === this.props.info.attachmentLocalId);
        const nextIndex = index === 0
            ? this.props.info.attachmentLocalIds.length - 1
            : index - 1;
        this.storeDispatch('updateDialogInfo', this.props.dialogId, {
            attachmentLocalId: this.props.info.attachmentLocalIds[nextIndex],
        });
    }

    /**
     * Prompt the browser print of this attachment.
     *
     * @private
     */
    _print() {
        const printWindow = window.open('about:blank', '_new');
        printWindow.document.open();
        printWindow.document.write(`
            <html>
                <head>
                    <script>
                        function onloadImage() {
                            setTimeout('printImage()', 10);
                        }
                        function printImage() {
                            window.print();
                            window.close();
                        }
                    </script>
                </head>
                <body onload='onloadImage()'>
                    <img src="${this.src}" alt=""/>
                </body>
            </html>`);
        printWindow.document.close();
    }

    /**
     * Rotate the image by 90 degrees to the right.
     *
     * @private
     */
    _rotate() {
        this.state.angle += 90;
    }

    /**
     * Stop dragging interaction of the user.
     *
     * @private
     */
    _stopDragging() {
        this._isDragging = false;
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
     * @return {string}
     */
    _updateZoomerStyle() {
        const tx = this._imageRef.el.offsetWidth * this.state.scale > this._zoomerRef.el.offsetWidth
            ? this._translate.x + this._translate.dx
            : 0;
        const ty = this._imageRef.el.offsetHeight * this.state.scale > this._zoomerRef.el.offsetHeight
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
    _zoomIn({ scroll=false }={}) {
        this.state.scale = this.state.scale + (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP);
        this._updateZoomerStyle();
    }

    /**
     * Zoom out the image.
     *
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.scroll=false]
     */
    _zoomOut({ scroll=false }={}) {
        if (this.state.scale === MIN_SCALE) {
            return;
        }
        this.state.scale = Math.max(MIN_SCALE, this.state.scale - (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP));
        this._updateZoomerStyle();
    }

    /**
     * Reset the zoom scale of the image.
     *
     * @private
     */
    _zoomReset() {
        this.state.scale = 1;
        this._updateZoomerStyle();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on mask of attachment viewer.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (this._isDragging) {
            return;
        }
        // TODO SEB clicking on the background should probably be handled by the dialog?
        this._close();
    }

    /**
     * Called when clicking on cross icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        this._close();
    }

    /**
     * Called when clicking on download icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDownload(ev) {
        this._download();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGlobal(ev) {
        if (!this._isDragging) {
            return;
        }
        ev.stopPropagation();
        this._stopDragging();
    }

    /**
     * Called when clicking on the header. Stop propagation of event to prevent
     * closing the dialog.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickHeader(ev) {
        ev.stopPropagation();
    }

    /**
     * Called when clicking on image. Stop propagation of event to prevent
     * closing the dialog.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickImage(ev) {
        if (this._isDragging) {
            return;
        }
        ev.stopPropagation();
    }

    /**
     * Called when clicking on next icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNext(ev) {
        this._next();
    }

    /**
     * Called when clicking on previous icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrevious(ev) {
        this._previous();
    }

    /**
     * Called when clicking on print icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrint(ev) {
        this._print();
    }

    /**
     * Called when clicking on rotate icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRotate(ev) {
        this._rotate();
    }

    /**
     * Called when clicking on embed video player. Stop propagation to prevent
     * closing the dialog.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickVideo(ev) {
        ev.stopPropagation();
    }

    /**
     * Called when clicking on zoom in icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomIn(ev) {
        this._zoomIn();
    }

    /**
     * Called when clicking on zoom out icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomOut(ev) {
        this._zoomOut();
    }

    /**
     * Called when clicking on reset zoom icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomReset(ev) {
        this._zoomReset();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        switch (ev.key) {
            case 'ArrowRight':
                this._next();
                break;
            case 'ArrowLeft':
                this._previous();
                break;
            case 'Escape':
                this._close();
                break;
            case 'q':
                this._close();
                break;
            case 'r':
                this._rotate();
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
     * Called when new image has been loaded
     *
     * @private
     * @param {Event} ev
     */
    _onLoadImage(ev) {
        ev.stopPropagation();
        this.state.isImageLoading = false;
    }

    /**
     * @private
     * @param {DragEvent} ev
     */
    _onMousedownImage(ev) {
        if (this._isDragging) {
            return;
        }
        if (ev.button !== 0) {
            return;
        }
        ev.stopPropagation();
        this._isDragging = true;
        this._dragstartX = ev.clientX;
        this._dragstartY = ev.clientY;
    }

    /**
     * @private
     * @param {DragEvent}
     */
    _onMousemoveView(ev) {
        if (!this._isDragging) {
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
        if (!this.el) {
            return;
        }
        if (ev.deltaY > 0) {
            this._zoomIn({ scroll: true });
        } else {
            this._zoomOut({ scroll: true });
        }
    }
}

AttachmentViewer.props = {
    id: String,
    info: {
        type: Object,
        shape: {
            attachmentLocalId: String,
            attachmentLocalIds: {
                type: Array,
                element: String,
            }
        },
    },
};

AttachmentViewer.template = 'mail.component.AttachmentViewer';

QWeb.registerComponent('AttachmentViewer', AttachmentViewer);

return AttachmentViewer;

});
