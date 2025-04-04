import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { useAutofocus, useLazyExternalListener, useService } from "@web/core/utils/hooks";
import { hidePDFJSButtons } from "@web/core/utils/pdfjs";

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
        this.zoomerRef = useRef("zoomer");
        this.iframeViewerPdfRef = useRef("iframeViewerPdf");
        this.hasTouch = hasTouch();

        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;

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
        if (this.hasTouch) {
            useLazyExternalListener(() => this.imageRef.el, "touchstart", this.onDragStartImage);
            useLazyExternalListener(() => this.imageRef.el, "touchmove", this.onDragMoveImage);
            useLazyExternalListener(() => this.imageRef.el, "touchend", this.onDragEndImage);
        }
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
     * @param {WheelEvent} ev
     */
    onWheelImage(ev) {
        if (ev.deltaY > 0) {
            this.zoomOut({ scroll: true });
        } else {
            this.zoomIn({ scroll: true });
        }
    }

    /**
     * @param {DragEvent | TouchEvent} ev
     */
    onDragStartImage(ev) {
        if (this.isDragging) {
            return;
        }
        if (ev instanceof MouseEvent && ev.button !== 0) {
            return;
        }
        this.isDragging = true;
        const { clientX, clientY } = ev instanceof MouseEvent ? ev : ev.touches[0];
        this.dragStartX = clientX;
        this.dragStartY = clientY;
        ev.preventDefault();
    }

    onDragEndImage() {
        if (!this.isDragging) {
            return;
        }
        this.isDragging = false;
        this.translate.x += this.translate.dx;
        this.translate.y += this.translate.dy;
        this.translate.dx = 0;
        this.translate.dy = 0;
        this.updateZoomerStyle();
    }

    /**
     * @param {DragEvent | TouchEvent} ev
     */
    onDragMoveImage(ev) {
        if (!this.isDragging) {
            return;
        }
        const { clientX, clientY } = ev instanceof MouseEvent ? ev : ev.touches[0];
        this.translate.dx = clientX - this.dragStartX;
        this.translate.dy = clientY - this.dragStartY;
        this.updateZoomerStyle();
        ev.preventDefault();
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
        const imageEl = this.imageRef.el;
        const imageWidth =
            (isImageRotated ? imageEl.offsetHeight : imageEl.offsetWidth) * this.state.scale;
        const imageHeight =
            (isImageRotated ? imageEl.offsetWidth : imageEl.offsetHeight) * this.state.scale;
        const tx =
            imageWidth > this.zoomerRef.el.offsetWidth ? this.translate.x + this.translate.dx : 0;
        const ty =
            imageHeight > this.zoomerRef.el.offsetHeight ? this.translate.y + this.translate.dy : 0;
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
