import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { clamp } from "@web/core/utils/numbers";
import { hidePDFJSButtons } from "@web/core/utils/pdfjs";

const IMAGE_BUFFER_PADDING = 20;

/**
 * @typedef {Object} File
 * @property {string} name
 * @property {string} downloadUrl
 * @property {boolean} [isImage]
 * @property {boolean} [isPdf]
 * @property {boolean} [isVideo]
 * @property {boolean} [isText]
 * @property {string} [defaultSource]
 * @property {boolean} [isUrlYoutube]
 * @property {string} [mimetype]
 * @property {boolean} [isViewable]
 * @typedef {Object} Props
 * @property {Array<File>} files
 * @property {number} startIndex
 * @property {function} close
 * @property {boolean} [modal]
 * @extends {Component<Props, Env>}
 */
export class FileViewer extends Component {
    static template = "web.FileViewer";
    static components = {};
    static props = ["files", "startIndex", "close?", "modal?"];
    static defaultProps = {
        modal: true,
    };

    setup() {
        useAutofocus();
        this.imageRef = useRef("image");
        this.imageToolbarRef = useRef("imageToolbar");
        this.zoomerRef = useRef("zoomer");
        this.iframeViewerPdfRef = useRef("iframeViewerPdf");
        this.hasTouch = hasTouch();

        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.dragTouchIdentifier = null;
        this.initialPinchDistance = null;
        this.initialScale = 1;

        this.scrollZoomStep = 0.1;
        this.zoomStep = 0.5;
        this.minScale = 0.5;
        this.translate = {
            dx: 0,
            dy: 0,
            x: 0,
            y: 0,
        };

        this.state = useState({
            index: this.props.startIndex,
            file: this.props.files[this.props.startIndex],
            imageLoaded: false,
            scale: 1,
            angle: 0,
        });
        this.ui = useService("ui");
        useEffect(
            (el) => {
                if (el) {
                    hidePDFJSButtons(this.iframeViewerPdfRef.el, {
                        hideDownload: true,
                        hidePrint: true,
                    });
                }
            },
            () => [this.iframeViewerPdfRef.el]
        );
    }

    onImageLoaded() {
        this.state.imageLoaded = true;
    }

    close() {
        this.props.close && this.props.close();
    }

    next() {
        const last = this.props.files.length - 1;
        this.activateFile(this.state.index === last ? 0 : this.state.index + 1);
    }

    previous() {
        const last = this.props.files.length - 1;
        this.activateFile(this.state.index === 0 ? last : this.state.index - 1);
    }

    activateFile(index) {
        this.state.index = index;
        this.state.file = this.props.files[index];
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowRight":
                this.next();
                break;
            case "ArrowLeft":
                this.previous();
                break;
            case "Escape":
                this.close();
                break;
            case "q":
                this.close();
                break;
        }
        if (this.state.file.isImage) {
            switch (ev.key) {
                case "r":
                    this.rotate();
                    break;
                case "+":
                    this.zoomIn();
                    break;
                case "-":
                    this.zoomOut();
                    break;
                case "0":
                    this.resetZoom();
                    break;
            }
        }
    }

    /**
     * @param {Event} ev
     */
    onWheelImage(ev) {
        if (ev.deltaY > 0) {
            this.zoomOut({ scroll: true });
        } else {
            this.zoomIn({ scroll: true });
        }
    }

    startImageDrag({ clientX, clientY }) {
        this.dragStartX = clientX;
        this.dragStartY = clientY;
    }

    updateImageDrag({ clientX, clientY }) {
        this.translate.dx = clientX - this.dragStartX;
        this.translate.dy = clientY - this.dragStartY;
        this.updateZoomerStyle();
    }

    endImageDrag() {
        this.translate.x += this.translate.dx;
        this.translate.y += this.translate.dy;
        this.translate.dx = 0;
        this.translate.dy = 0;
        this.updateZoomerStyle();
    }

    /** @param {DragEvent} ev */
    onMouseDownImage(ev) {
        if (this.isDragging) {
            return;
        }
        if (ev.button !== 0) {
            return;
        }
        this.isDragging = true;
        this.startImageDrag(ev);
    }

    /** @param {DragEvent} ev */
    onMouseMoveImage(ev) {
        if (!this.isDragging) {
            return;
        }
        this.updateImageDrag(ev);
    }

    onMouseUpImage() {
        if (!this.isDragging) {
            return;
        }
        this.endImageDrag();
        this.isDragging = false;
    }

    /** @param {TouchEvent} ev */
    onTouchStartImage(ev) {
        if (ev.touches.length === 1) {
            if (this.dragTouchIdentifier !== null) {
                return;
            }
            this.dragTouchIdentifier = ev.touches[0].identifier;
            this.startImageDrag(ev.touches[0]);
        } else if (ev.touches.length === 2) {
            this.initialPinchDistance = Math.hypot(
                ev.touches[0].clientX - ev.touches[1].clientX,
                ev.touches[0].clientY - ev.touches[1].clientY
            );
            this.initialScale = this.state.scale;
        }
    }

    /** @param {TouchEvent} ev */
    onTouchMoveImage(ev) {
        if (!this.state.file.isImage) {
            return;
        }
        if (ev.touches.length === 1) {
            if (ev.touches[0].identifier !== this.dragTouchIdentifier) {
                return;
            }
            this.updateImageDrag(ev.touches[0]);
        } else if (ev.touches.length === 2 && this.initialPinchDistance !== null) {
            const currentPinchDistance = Math.hypot(
                ev.touches[0].clientX - ev.touches[1].clientX,
                ev.touches[0].clientY - ev.touches[1].clientY
            );
            const scaleFactor = currentPinchDistance / this.initialPinchDistance;
            this.state.scale = Math.max(this.minScale, this.initialScale * scaleFactor);
            this.updateZoomerStyle();
        }
    }

    /** @param {TouchEvent} ev */
    onTouchEndImage(ev) {
        if (ev.touches.length < 2) {
            this.initialPinchDistance = null;
        }
        if (this.dragTouchIdentifier === null) {
            return;
        }
        for (let index = 0; index < ev.touches.length; index++) {
            if (ev.touches[index].identifier === this.dragTouchIdentifier) {
                return;
            }
        }
        this.endImageDrag();
        this.dragTouchIdentifier = null;
    }

    resetZoom() {
        this.state.scale = 1;
        this.updateZoomerStyle();
    }

    rotate() {
        this.state.angle += 90;
        this.updateZoomerStyle();
    }

    /**
     * @param {{ scroll?: boolean }}
     */
    zoomIn({ scroll = false } = {}) {
        this.state.scale = this.state.scale + (scroll ? this.scrollZoomStep : this.zoomStep);
        this.updateZoomerStyle();
    }

    /**
     * @param {{ scroll?: boolean }}
     */
    zoomOut({ scroll = false } = {}) {
        if (this.state.scale === this.minScale) {
            return;
        }
        const unflooredAdaptedScale =
            this.state.scale - (scroll ? this.scrollZoomStep : this.zoomStep);
        this.state.scale = Math.max(this.minScale, unflooredAdaptedScale);
        this.updateZoomerStyle();
    }

    updateZoomerStyle() {
        const isImageRotated = this.state.angle % 180 !== 0;
        const { offsetWidth, offsetHeight } = this.imageRef.el;
        const imageWidth = (isImageRotated ? offsetHeight : offsetWidth) * this.state.scale;
        const imageHeight = (isImageRotated ? offsetWidth : offsetHeight) * this.state.scale;
        const diffX = imageWidth - this.zoomerRef.el.offsetWidth + IMAGE_BUFFER_PADDING;
        const diffY =
            imageHeight -
            this.zoomerRef.el.offsetHeight +
            2 * this.imageToolbarRef.el.clientHeight +
            IMAGE_BUFFER_PADDING;
        let tx = diffX > 0 ? this.translate.x + this.translate.dx : 0;
        let ty = diffY > 0 ? this.translate.y + this.translate.dy : 0;
        if (diffX > 0) {
            const limitX = diffX / 2;
            tx = clamp(tx, -limitX, limitX);
            this.translate.dx = tx - this.translate.x;
        }
        if (diffY > 0) {
            const limitY = diffY / 2;
            ty = clamp(ty, -limitY, limitY);
            this.translate.dy = ty - this.translate.y;
        }
        if (tx === 0) {
            this.translate.x = 0;
        }
        if (ty === 0) {
            this.translate.y = 0;
        }
        this.zoomerRef.el.style = "transform: " + `translate(${tx}px, ${ty}px)`;
    }

    get imageStyle() {
        let style =
            "transform: " +
            `scale3d(${this.state.scale}, ${this.state.scale}, 1) ` +
            `rotate(${this.state.angle}deg);`;

        if (this.state.angle % 180 !== 0) {
            style += `max-height: ${window.innerWidth}px; max-width: ${window.innerHeight}px;`;
        } else {
            style += "max-height: 100%; max-width: 100%;";
        }
        style += `background: repeating-conic-gradient(#ccc 0deg 90deg, #fff 90deg 180deg) 50% / 20px 20px;`;
        return style;
    }

    onClickPrint() {
        const printWindow = window.open("about:blank", "_new");
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
                        <img src="${this.state.file.defaultSource}" alt=""/>
                    </body>
                </html>`);
        printWindow.document.close();
    }
}
