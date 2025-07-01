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

export class ImageTransformation extends Component {
    static template = "html_editor.ImageTransformation";
    static props = {
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        image: { validate: (p) => p.tagName === "IMG" },
        destroy: { type: Function },
        onChange: { type: Function },
    };

    setup() {
        this.document = this.props.document;
        this.image = this.props.image;
        this.transfoContainer = useRef("transfoContainer");
        this.transfoControls = useRef("transfoControls");
        this.transfoCenter = useRef("transfoCenter");
        this.computeImageTransformations();
        onMounted(() => {
            this.positionTransfoContainer();
        });
        useExternalListener(window, "mousemove", this.mouseMove);
        useExternalListener(window, "mouseup", this.mouseUp);
        // When a character key is pressed and the image gets deleted,
        // close the image transform via selectionchange.
        useExternalListener(this.document, "selectionchange", () => this.props.destroy());
        // Backspace/Delete don’t trigger selectionchange on image
        // delete in Chrome, so we use keydown event.
        useExternalListener(this.document, "keydown", (ev) => {
            if (["Backspace", "Delete"].includes(ev.key)) {
                this.props.destroy();
            }
        });
        useHotkey("escape", () => this.props.destroy());
        usePositionHook({ el: this.props.editable }, this.document, this.resetHandlers);
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
            const dang =
                Math.atan(
                    (settings.width * settings.scalex) / (settings.height * settings.scaley)
                ) / rad;

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
            if (settings.scaley < 0 && settings.scalex < 0) {
                ang += 180;
            }

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
            const angle = settings.angle * rad;
            const dx = cdx * Math.cos(angle) - cdy * Math.sin(-angle);
            const dy = -cdx * Math.sin(angle) + cdy * Math.cos(-angle);
            if (this.transfo.active.type.indexOf("t") != -1) {
                settings.scaley = dy / (settings.height / 2);
            }
            if (this.transfo.active.type.indexOf("b") != -1) {
                settings.scaley = -dy / (settings.height / 2);
            }
            if (this.transfo.active.type.indexOf("l") != -1) {
                settings.scalex = dx / (settings.width / 2);
            }
            if (this.transfo.active.type.indexOf("r") != -1) {
                settings.scalex = -dx / (settings.width / 2);
            }
            if (settings.scaley > 0 && settings.scaley < 0.05) {
                settings.scaley = 0.05;
            }
            if (settings.scalex > 0 && settings.scalex < 0.05) {
                settings.scalex = 0.05;
            }
            if (settings.scaley < 0 && settings.scaley > -0.05) {
                settings.scaley = -0.05;
            }
            if (settings.scalex < 0 && settings.scalex > -0.05) {
                settings.scalex = -0.05;
            }

            if (
                ev.shiftKey &&
                (this.transfo.active.type === "tl" ||
                    this.transfo.active.type === "bl" ||
                    this.transfo.active.type === "tr" ||
                    this.transfo.active.type === "br")
            ) {
                settings.scaley = settings.scalex;
            }
        }

        settings.angle = Math.round(settings.angle);
        settings.translatex = Math.round(settings.translatex);
        settings.translatey = Math.round(settings.translatey);
        settings.scalex = Math.round(settings.scalex * 100) / 100;
        settings.scaley = Math.round(settings.scaley * 100) / 100;
        this.positionTransfoContainer();
        this.props.onChange();
    }

    mouseUp() {
        this.transfo.active = null;
    }

    mouseDown(ev) {
        if (this.transfo.active) {
            return;
        }
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
            scalex: this.transfo.settings.scalex,
            scaley: this.transfo.settings.scaley,
            pageX: ev.pageX,
            pageY: ev.pageY,
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
        this.transfo.settings.scalex =
            transform.indexOf("scaleX") != -1
                ? parseFloat(transform.match(/scaleX\(([^)]+)\)/)[1])
                : 1;
        this.transfo.settings.scaley =
            transform.indexOf("scaleY") != -1
                ? parseFloat(transform.match(/scaleY\(([^)]+)\)/)[1])
                : 1;

        this.image.style.transform = "";

        this.transfo.settings.pos = this.getOffset(this.image);

        this.transfo.settings.height = this.image.clientHeight;
        this.transfo.settings.width = this.image.clientWidth;

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
        const width = parseFloat(settings.css.width);
        const height = parseFloat(settings.css.height);
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

        for (const child of controls.children) {
            child.style.transform =
                "scaleX(" + 1 / settings.scalex + ") scaleY(" + 1 / settings.scaley + ")";
        }
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
        if (this.transfo.settings.scalex != 1) {
            transform += " scaleX(" + this.transfo.settings.scalex + ") ";
        }
        if (this.transfo.settings.scaley != 1) {
            transform += " scaleY(" + this.transfo.settings.scaley + ") ";
        }
        element.style.transform = transform;
    }

    getOffset(target) {
        if (!target.getClientRects().length) {
            return { top: 0, left: 0 };
        } else {
            const rect = target.getBoundingClientRect();
            const win = target.ownerDocument.defaultView;
            const frameElement = target.ownerDocument.defaultView.frameElement;
            const offset = { top: 0, left: 0 };
            if (frameElement) {
                const frameRect = frameElement.getBoundingClientRect();
                offset.left += frameRect.left;
                offset.top += frameRect.top;
            }
            return {
                top: rect.top + win.pageYOffset + offset.top,
                left: rect.left + win.pageXOffset + offset.left,
            };
        }
    }

    resetHandlers() {
        this.computeImageTransformations();
        this.positionTransfoContainer();
    }
}
