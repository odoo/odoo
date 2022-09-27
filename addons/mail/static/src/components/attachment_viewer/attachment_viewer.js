/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onPatched, onWillUnmount } = owl;

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
        this.attachmentViewer.stopDragging();
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
                this.attachmentViewer.zoomIn();
                break;
            case '-':
                this.attachmentViewer.zoomOut();
                break;
            case '0':
                this.attachmentViewer.resetZoom();
                break;
            default:
                return;
        }
        ev.stopPropagation();
    }

}

Object.assign(AttachmentViewer, {
    props: { record: Object },
    template: 'mail.AttachmentViewer',
});

registerMessagingComponent(AttachmentViewer);
