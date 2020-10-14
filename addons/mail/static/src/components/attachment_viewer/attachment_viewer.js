odoo.define('mail/static/src/components/attachment_viewer/attachment_viewer.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component, QWeb } = owl;
const { useRef } = owl.hooks;

const MIN_SCALE = 0.5;
const SCROLL_ZOOM_STEP = 0.1;
const ZOOM_STEP = 0.5;

class AttachmentViewer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.MIN_SCALE = MIN_SCALE;
        useStore(props => {
            const attachmentViewer = this.env.models['mail.attachment_viewer'].get(props.localId);
            return {
                attachment: attachmentViewer && attachmentViewer.attachment
                    ? attachmentViewer.attachment.__state
                    : undefined,
                attachments: attachmentViewer
                    ? attachmentViewer.attachments.map(attachment => attachment.__state)
                    : [],
                attachmentViewer: attachmentViewer ? attachmentViewer.__state : undefined,
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
         * not observed with `useStore` because they are used to compute zoomer
         * style, and this is changed directly on zoomer for performance
         * reasons (overhead of making vdom is too significant for each mouse
         * position changes while dragging)
         */
        this._translate = { x: 0, y: 0, dx: 0, dy: 0 };
        /**
         * Tracked last rendered attachment. Useful to detect a new image is
         * loading, in order to display spinner until it is fully loaded.
         */
        this._renderedAttachment = undefined;
        this._onClickGlobal = this._onClickGlobal.bind(this);
    }

    mounted() {
        this.el.focus();
        this._handleImageLoad();
        this._renderedAttachment = this.attachmentViewer.attachment;
        document.addEventListener('click', this._onClickGlobal);
    }

    /**
     * When a new image is displayed, show a spinner until it is loaded.
     */
    patched() {
        this._handleImageLoad();
        this._renderedAttachment = this.attachmentViewer.attachment;
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickGlobal);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment_viewer}
     */
    get attachmentViewer() {
        return this.env.models['mail.attachment_viewer'].get(this.props.localId);
    }

    /**
     * Compute the style of the image (scale + rotation).
     *
     * @returns {string}
     */
    get imageStyle() {
        const attachmentViewer = this.attachmentViewer;
        let style = `transform: ` +
            `scale3d(${attachmentViewer.scale}, ${attachmentViewer.scale}, 1) ` +
            `rotate(${attachmentViewer.angle}deg);`;

        if (attachmentViewer.angle % 180 !== 0) {
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

    /**
     * Mandatory method for dialog components.
     * Prevent closing the dialog when clicking on the mask when the user is
     * currently dragging the image.
     *
     * @returns {boolean}
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
        this.attachmentViewer.close();
    }

    /**
     * Download the attachment.
     *
     * @private
     */
    _download() {
        const id = this.attachmentViewer.attachment.id;
        this.env.services.navigate(`/web/content/ir.attachment/${id}/datas`, { download: true });
    }

    /**
     * Determine whether the current image is rendered for the 1st time, and if
     * that's the case, display a spinner until loaded.
     *
     * @private
     */
    _handleImageLoad() {
        if (
            this.attachmentViewer.attachment.fileType === 'image' &&
            this._renderedAttachment !== this.attachmentViewer.attachment
        ) {
            this.attachmentViewer.update({ isImageLoading: true });
            this._imageRef.el.addEventListener('load', ev => this._onLoadImage(ev));
        }
    }

    /**
     * Display the previous attachment in the list of attachments.
     *
     * @private
     */
    _next() {
        const attachmentViewer = this.attachmentViewer;
        const index = attachmentViewer.attachments.findIndex(attachment =>
            attachment === attachmentViewer.attachment
        );
        const nextIndex = (index + 1) % attachmentViewer.attachments.length;
        attachmentViewer.update({
            attachment: [['link', attachmentViewer.attachments[nextIndex]]],
        });
    }

    /**
     * Display the previous attachment in the list of attachments.
     *
     * @private
     */
    _previous() {
        const attachmentViewer = this.attachmentViewer;
        const index = attachmentViewer.attachments.findIndex(attachment =>
            attachment === attachmentViewer.attachment
        );
        const nextIndex = index === 0
            ? attachmentViewer.attachments.length - 1
            : index - 1;
        attachmentViewer.update({
            attachment: [['link', attachmentViewer.attachments[nextIndex]]],
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
                    <img src="${this.attachmentViewer.attachment.defaultSource}" alt=""/>
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
        this.attachmentViewer.update({ angle: this.attachmentViewer.angle + 90 });
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
     * @returns {string}
     */
    _updateZoomerStyle() {
        const attachmentViewer = this.attachmentViewer;
        const tx = this._imageRef.el.offsetWidth * attachmentViewer.scale > this._zoomerRef.el.offsetWidth
            ? this._translate.x + this._translate.dx
            : 0;
        const ty = this._imageRef.el.offsetHeight * attachmentViewer.scale > this._zoomerRef.el.offsetHeight
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
     * Called when clicking on mask of attachment viewer.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (this._isDragging) {
            return;
        }
        // TODO: clicking on the background should probably be handled by the dialog?
        // task-2092965
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
        ev.stopPropagation();
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
        ev.stopPropagation();
        this._next();
    }

    /**
     * Called when clicking on previous icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrevious(ev) {
        ev.stopPropagation();
        this._previous();
    }

    /**
     * Called when clicking on print icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrint(ev) {
        ev.stopPropagation();
        this._print();
    }

    /**
     * Called when clicking on rotate icon.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRotate(ev) {
        ev.stopPropagation();
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
        this.attachmentViewer.update({ isImageLoading: false });
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
        ev.stopPropagation();
        if (!this.el) {
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
    props: {
        localId: String,
    },
    template: 'mail.AttachmentViewer',
});

QWeb.registerComponent('AttachmentViewer', AttachmentViewer);

return AttachmentViewer;

});
