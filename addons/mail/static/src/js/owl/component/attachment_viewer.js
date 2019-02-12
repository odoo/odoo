odoo.define('mail.component.AttachmentViewer', function () {
'use strict';

const MIN_SCALE = 0.5;
const SCROLL_ZOOM_STEP = 0.1;
const ZOOM_STEP = 0.5;

class AttachmentViewer extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.MIN_SCALE = MIN_SCALE;
        this.state = owl.useState({
            angle: 0,
            isImageLoading: false,
            scale: 1,
        });
        this._imageRef = owl.hooks.useRef('image');
        this._translate = {
            x: 0,
            y: 0,
            dx: 0,
            dy: 0,
        };
        this._zoomerRef = owl.hooks.useRef('zoomer');
        this._globalClickEventListener = ev => this._onClickGlobal(ev);
    }

    mounted() {
        this.el.focus();
        this._handleImageLoad();
        this._renderedAttachmentLocalId = this.props.info.attachmentLocalId;
        document.addEventListener('click', this._globalClickEventListener);
    }

    patched() {
        this._handleImageLoad();
        this._renderedAttachmentLocalId = this.props.info.attachmentLocalId;
    }

    willUnmount() {
        document.removeEventListener('click', this._globalClickEventListener);
    }

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    /**
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
     * @return {boolean}
     */
    isCloseable() {
        return !this._dragging;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _close() {
        this.dispatch('closeDialog', this.props.dialogId);
    }

    /**
     * @private
     */
    _download() {
        window.location = `/web/content/ir.attachment/${this.storeProps.attachment.id}/datas?download=true`;
    }

    /**
     * @private
     */
    _handleImageLoad() {
        if (
            this.env.store.getters.attachmentFileType(this.props.info.attachmentLocalId) === 'image' &&
            this._renderedAttachmentLocalId !== this.props.info.attachmentLocalId
        ) {
            this.state.isImageLoading = true;
            this._imageRef.el.addEventListener('load', ev => this._onLoadImage(ev));
        }
    }

    /**
     * @private
     */
    _next() {
        const index = this.props.info.attachmentLocalIds.findIndex(localId =>
            localId === this.props.info.attachmentLocalId);
        const nextIndex = (index + 1) % this.props.info.attachmentLocalIds.length;
        this.dispatch('updateDialogInfo', this.props.dialogId, {
            attachmentLocalId: this.props.info.attachmentLocalIds[nextIndex],
        });
    }

    /**
     * @private
     */
    _previous() {
        const index = this.props.info.attachmentLocalIds.findIndex(localId =>
            localId === this.props.info.attachmentLocalId);
        const nextIndex = index === 0
            ? this.props.info.attachmentLocalIds.length - 1
            : index - 1;
        this.dispatch('updateDialogInfo', this.props.dialogId, {
            attachmentLocalId: this.props.info.attachmentLocalIds[nextIndex],
        });
    }

    /**
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
     * @private
     */
    _rotate() {
        this.state.angle += 90;
    }

    /**
     * @private
     */
    _stopDragging() {
        this._dragging = false;
        this._translate.x += this._translate.dx;
        this._translate.y += this._translate.dy;
        this._translate.dx = 0;
        this._translate.dy = 0;
        this._updateZoomerStyle();
    }

    /**
     * @private
     * @return {string}
     */
    _updateZoomerStyle() {
        const tx = this._imageRef.el.offsetWidth*this.state.scale > this._zoomerRef.el.offsetWidth
            ? this._translate.x + this._translate.dx
            : 0;
        const ty = this._imageRef.el.offsetHeight*this.state.scale > this._zoomerRef.el.offsetHeight
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
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.scroll=false]
     */
    _zoomIn({ scroll=false }={}) {
        this.state.scale = this.state.scale + (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP);
        this._updateZoomerStyle();
    }

    /**
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.scroll=false]
     */
    _zoomOut({ scroll=false }={}) {
        if (this.state.scale === MIN_SCALE) { return; }
        this.state.scale = Math.max(MIN_SCALE, this.state.scale - (scroll ? SCROLL_ZOOM_STEP : ZOOM_STEP));
        this._updateZoomerStyle();
    }

    /**
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
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (this._dragging) { return; }
        this._close();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        this._close();
    }

    /**
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
        if (!this._dragging) { return; }
        ev.stopPropagation();
        this._stopDragging();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickHeader(ev) {
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickImage(ev) {
        if (this._dragging) { return; }
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNext(ev) {
        this._next();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrevious(ev) {
        this._previous();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPrint(ev) {
        this._print();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRotate(ev) {
        this._rotate();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickVideo(ev) {
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomIn(ev) {
        this._zoomIn();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickZoomOut(ev) {
        this._zoomOut();
    }

    /**
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
        if (this._dragging) { return; }
        if (ev.button !== 0) { return; }
        ev.stopPropagation();
        this._dragging = true;
        this._dragstartX = ev.clientX;
        this._dragstartY = ev.clientY;
    }

    /**
     * @private
     * @param {DragEvent}
     */
    _onMousemoveView(ev) {
        if (!this._dragging) { return; }
        this._translate.dx = ev.clientX - this._dragstartX;
        this._translate.dy = ev.clientY - this._dragstartY;
        // $image.css('cursor', 'move');
        this._updateZoomerStyle();
    }

    /**
     * @private
     * @param {Event} ev
     */
    _onWheelImage(ev) {
        if (!this.el) { return; }
        if (ev.deltaY > 0) {
            this._zoomIn({ scroll: true });
        } else {
            this._zoomOut({ scroll: true });
        }
    }
}

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {Object} ownProps.info
 * @param {string} ownProps.info.attachmentLocalId
 */
AttachmentViewer.mapStoreToProps = function (state, ownProps) {
    return {
        attachment: state.attachments[ownProps.info.attachmentLocalId],
    };
};

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

owl.QWeb.registerComponent('AttachmeentViewer', AttachmentViewer);

return AttachmentViewer;

});
