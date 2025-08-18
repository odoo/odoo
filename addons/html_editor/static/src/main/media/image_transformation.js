/*
Copyright (c) 2014 Christophe Matthieu,

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
*/

import { Component, onMounted, useExternalListener, useRef } from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { usePositionHook } from "@html_editor/position_hook";

const rad = Math.PI / 180;
const MIN_IMAGE_SIZE = 20;

export class ImageTransformation extends Component {
    static template = "html_editor.ImageTransformation";
    static props = {
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        image: { validate: (p) => p.tagName === "IMG" },
        destroy: { type: Function },
        onChange: { type: Function },
        onApply: { type: Function, optional: true },
        onComponentMounted: { type: Function, optional: true },
    };
    static defaultProps = {
        onComponentMounted: () => {},
    };

    setup() {
        this.isCurrentlyTransforming = false;
        this.document = this.props.document;
        this.image = this.props.image;
        this.transfoContainer = useRef("transfoContainer");
        this.transfoControls = useRef("transfoControls");
        this.transfoCenter = useRef("transfoCenter");
        this.computeImageTransformations();
        onMounted(() => {
            this.positionTransfoContainer();
            this.props.onComponentMounted();
        });
        useExternalListener(window, "mousemove", this.mouseMove);
        useExternalListener(window, "mouseup", this.mouseUp);
        if (this.document.defaultView.frameElement) {
            const iframeWindow = this.document.defaultView;
            useExternalListener(iframeWindow, "mousemove", this.mouseMove);
            useExternalListener(iframeWindow, "mouseup", this.mouseUp);
        }
        // When a character key is pressed and the image gets deleted,
        // close the image transform via selectionchange.
        useExternalListener(this.document, "selectionchange", () => this.destroy());
        // Backspace/Delete don’t trigger selectionchange on image
        // delete in Chrome, so we use keydown event.
        useExternalListener(this.document, "keydown", (ev) => {
            if (["Backspace", "Delete"].includes(ev.key)) {
                this.destroy();
            }
        });
        useHotkey("escape", () => this.destroy());
        usePositionHook({ el: this.props.editable }, this.document, () => {
            if (!this.isCurrentlyTransforming) {
                this.resetHandlers();
            }
        });
    }

    destroy() {
        this.props.onApply?.();
        this.props.destroy();
    }

    mouseMove(ev) {
        if (!this.transfo.active) {
            return;
        }
        ev.preventDefault();
        const settings = this.transfo.settings;
        const center = this.transfo.active.center;
        const cdx = center.left - ev.pageX;
        const cdy = center.top - ev.pageY;
        if (this.transfo.active.type == "rotator") {
            let ang;
            const dang = Math.atan(settings.width / settings.height) / rad;

            if (cdy) {
                ang = Math.atan(-cdx / cdy) / rad;
            } else {
                ang = 0;
            }
            if (ev.pageY >= center.top && ev.pageX >= center.left) {
                ang += 180;
            } else if (ev.pageY >= center.top && ev.pageX < center.left) {
                ang += 180;
            } else if (ev.pageY < center.top && ev.pageX < center.left) {
                ang += 360;
            }

            ang -= dang;

            if (!ev.ctrlKey) {
                settings.angle =
                    Math.round(ang / this.transfo.settings.rotationStep) *
                    this.transfo.settings.rotationStep;
            } else {
                settings.angle = ang;
            }

            // reset position : don't move center
            this.positionTransfoContainer();
            const new_center = this.getOffset(this.transfoCenter.el);
            const x = center.left - new_center.left;
            const y = center.top - new_center.top;
            const angle = ang * rad;
            settings.translatex += x * Math.cos(angle) - y * Math.sin(-angle);
            settings.translatey += -x * Math.sin(angle) + y * Math.cos(-angle);
        } else if (this.transfo.active.type == "position") {
            const angle = settings.angle * rad;
            const x = ev.pageX - this.transfo.active.pageX;
            const y = ev.pageY - this.transfo.active.pageY;
            this.transfo.active.pageX = ev.pageX;
            this.transfo.active.pageY = ev.pageY;
            const dx = x * Math.cos(angle) - y * Math.sin(-angle);
            const dy = -x * Math.sin(angle) + y * Math.cos(-angle);

            settings.translatex += dx;
            settings.translatey += dy;
        } else if (this.transfo.active.type.length === 2) {
            const width = this.transfo.active.width;
            const height = this.transfo.active.height;
            const deltaX = ev.pageX - this.transfo.active.pageX;
            const deltaY = ev.pageY - this.transfo.active.pageY;

            let newWidth = width;
            let newHeight = height;

            if (this.transfo.active.type.indexOf("t") != -1) {
                newHeight = height - deltaY;
            }
            if (this.transfo.active.type.indexOf("b") != -1) {
                newHeight = height + deltaY;
            }
            if (this.transfo.active.type.indexOf("l") != -1) {
                newWidth = width - deltaX;
            }
            if (this.transfo.active.type.indexOf("r") != -1) {
                newWidth = width + deltaX;
            }

            // Ensure minimum dimensions
            if (newWidth < MIN_IMAGE_SIZE) {
                newWidth = MIN_IMAGE_SIZE;
            }
            if (newHeight < MIN_IMAGE_SIZE) {
                newHeight = MIN_IMAGE_SIZE;
            }

            if (
                ev.shiftKey &&
                (this.transfo.active.type === "tl" ||
                    this.transfo.active.type === "bl" ||
                    this.transfo.active.type === "tr" ||
                    this.transfo.active.type === "br")
            ) {
                const aspectRatio = width / height;
                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    newHeight = newWidth / aspectRatio;
                } else {
                    newWidth = newHeight * aspectRatio;
                }
            }
            this.image.style.width = newWidth + "px";
            this.image.style.height = newHeight + "px";
            settings.width = newWidth;
            settings.height = newHeight;
        }

        settings.angle = Math.round(settings.angle);
        settings.translatex = Math.round(settings.translatex);
        settings.translatey = Math.round(settings.translatey);
        this.transfo.settings.pos = this.getOffset(this.image);
        this.positionTransfoContainer();
        this.props.onChange();
    }

    mouseUp() {
        this.isCurrentlyTransforming = false;
        this.transfo.active = null;
        this.props.onApply?.();
    }

    mouseDown(ev) {
        if (this.transfo.active) {
            return;
        }
        this.isCurrentlyTransforming = true;
        let type = "position";
        const target = ev.target.closest("div");

        if (target.classList.contains("transfo-rotator")) {
            type = "rotator";
        } else if (target.classList.contains("transfo-scaler-tl")) {
            type = "tl";
        } else if (target.classList.contains("transfo-scaler-tr")) {
            type = "tr";
        } else if (target.classList.contains("transfo-scaler-br")) {
            type = "br";
        } else if (target.classList.contains("transfo-scaler-bl")) {
            type = "bl";
        } else if (target.classList.contains("transfo-scaler-tc")) {
            type = "tc";
        } else if (target.classList.contains("transfo-scaler-bc")) {
            type = "bc";
        } else if (target.classList.contains("transfo-scaler-ml")) {
            type = "ml";
        } else if (target.classList.contains("transfo-scaler-mr")) {
            type = "mr";
        }

        this.transfo.active = {
            type: type,
            pageX: ev.pageX,
            pageY: ev.pageY,
            width: parseFloat(getComputedStyle(this.image).width),
            height: parseFloat(getComputedStyle(this.image).height),
            center: this.getOffset(this.transfoCenter.el),
        };
    }

    computeImageTransformations() {
        this.transfo = {};
        const transform = this.image.style.transform || "";

        this.transfo.settings = {};

        this.transfo.settings.angle =
            transform.indexOf("rotate") != -1
                ? parseFloat(transform.match(/rotate\(([^)]+)deg\)/)[1])
                : 0;

        this.image.style.transform = "";

        this.transfo.settings.pos = this.getOffset(this.image);
        this.transfo.settings.width = parseFloat(getComputedStyle(this.image).width);
        this.transfo.settings.height = parseFloat(getComputedStyle(this.image).height);

        const translatex = transform.match(/translateX\(([0-9.-]+)(%|px)\)/);
        const translatey = transform.match(/translateY\(([0-9.-]+)(%|px)\)/);
        this.transfo.settings.translate = "%";

        if (translatex && translatex[2] === "%") {
            this.transfo.settings.translatexp = parseFloat(translatex[1]);
            this.transfo.settings.translatex =
                (this.transfo.settings.translatexp / 100) * this.transfo.settings.width;
        } else {
            this.transfo.settings.translatex = translatex ? parseFloat(translatex[1]) : 0;
        }
        if (translatey && translatey[2] === "%") {
            this.transfo.settings.translateyp = parseFloat(translatey[1]);
            this.transfo.settings.translatey =
                (this.transfo.settings.translateyp / 100) * this.transfo.settings.height;
        } else {
            this.transfo.settings.translatey = translatey ? parseFloat(translatey[1]) : 0;
        }

        this.transfo.settings.css = window.getComputedStyle(this.image, null);
        this.transfo.settings.rotationStep = 5;
    }

    positionTransfoContainer() {
        const settings = this.transfo.settings;
        const width = parseFloat(getComputedStyle(this.image).width);
        const height = parseFloat(getComputedStyle(this.image).height);
        settings.translatexp = Math.round((settings.translatex / width) * 1000) / 10;
        settings.translateyp = Math.round((settings.translatey / height) * 1000) / 10;

        this.setImageTransformation(this.image);

        this.transfoContainer.el.style.position = "absolute";
        this.transfoContainer.el.style.width = width + "px";
        this.transfoContainer.el.style.height = height + "px";
        this.transfoContainer.el.style.top = settings.pos.top + "px";
        this.transfoContainer.el.style.left = settings.pos.left + "px";

        const controls = this.transfoControls.el;

        this.setImageTransformation(controls);
        controls.style.width = width + "px";
        controls.style.height = height + "px";
        controls.style.cursor = "move";
    }

    setImageTransformation(element) {
        let transform = "";
        if (this.transfo.settings.angle !== 0) {
            transform += " rotate(" + this.transfo.settings.angle + "deg) ";
        }
        if (this.transfo.settings.translatex) {
            transform +=
                " translateX(" +
                (this.transfo.settings.translate === "%"
                    ? this.transfo.settings.translatexp + "%"
                    : this.transfo.settings.translatex + "px") +
                ") ";
        }
        if (this.transfo.settings.translatey) {
            transform +=
                " translateY(" +
                (this.transfo.settings.translate === "%"
                    ? this.transfo.settings.translateyp + "%"
                    : this.transfo.settings.translatey + "px") +
                ") ";
        }
        element.style.transform = transform;
    }

    getOffset(target) {
        if (!target.getClientRects().length) {
            return { top: 0, left: 0 };
        } else {
            const rect = target.getBoundingClientRect();
            const frameElement = target.ownerDocument.defaultView.frameElement;
            const offset = { top: 0, left: 0 };
            if (frameElement) {
                const frameRect = frameElement.getBoundingClientRect();
                offset.left += frameRect.left;
                offset.top += frameRect.top;
            }
            return {
                top: rect.top + window.pageYOffset + offset.top,
                left: rect.left + window.pageXOffset + offset.left,
            };
        }
    }

    resetHandlers() {
        this.computeImageTransformations();
        this.positionTransfoContainer();
    }
}
