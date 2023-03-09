/* @odoo-module */

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {Array<T>} attachments
 * @extends {Component<Props, Env>}
 */
export class AttachmentViewer extends Component {
    static template = "mail.attachment_viewer";
    static components = {};
    static props = ["attachments", "startIndex", "close", "modal?"];
    static defaultProps = {
        modal: true,
    };

    setup() {
        this.imageRef = useRef("image");
        this.zoomerRef = useRef("zoomer");

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

        useExternalListener(document, "keydown", this.onKeydown);
        this.state = useState({
            index: this.props.startIndex,
            attachment: this.props.attachments[this.props.startIndex],
            imageLoaded: false,
            scale: 1,
            angle: 0,
        });
    }

    onImageLoaded() {
        this.state.imageLoaded = true;
    }

    close() {
        this.props.close();
    }

    next() {
        const last = this.props.attachments.length - 1;
        this.activateAttachment(this.state.index === last ? 0 : this.state.index + 1);
    }

    previous() {
        const last = this.props.attachments.length - 1;
        this.activateAttachment(this.state.index === 0 ? last : this.state.index - 1);
    }

    activateAttachment(index) {
        this.state.index = index;
        this.state.attachment = this.props.attachments[index];
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
            default:
                return;
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

    /**
     * @param {DragEvent} ev
     */
    onMousedownImage(ev) {
        if (this.isDragging) {
            return;
        }
        if (ev.button !== 0) {
            return;
        }
        this.isDragging = true;
        this.dragStartX = ev.clientX;
        this.dragStartY = ev.clientY;
    }

    onMouseupImage() {
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
     * @param {DragEvent}
     */
    onMousemoveView(ev) {
        if (!this.isDragging) {
            return;
        }
        this.translate.dx = ev.clientX - this.dragStartX;
        this.translate.dy = ev.clientY - this.dragStartY;
        this.updateZoomerStyle();
    }

    resetZoom() {
        this.state.scale = 1;
        this.updateZoomerStyle();
    }

    rotate() {
        this.state.angle += 90;
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
        const tx =
            this.imageRef.el.offsetWidth * this.state.scale > this.zoomerRef.el.offsetWidth
                ? this.translate.x + this.translate.dx
                : 0;
        const ty =
            this.imageRef.el.offsetHeight * this.state.scale > this.zoomerRef.el.offsetHeight
                ? this.translate.y + this.translate.dy
                : 0;
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
                        <img src="${this.state.attachment.imageUrl}" alt=""/>
                    </body>
                </html>`);
        printWindow.document.close();
    }
}
