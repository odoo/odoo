odoo.define('pos_restaurant.Resizeable', function(require) {
    'use strict';

    const { useExternalListener } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class Resizeable extends PosComponent {
        constructor() {
            super(...arguments);

            useExternalListener(document, 'mousemove', this.resizeN);
            useExternalListener(document, 'mouseup', this.endResizeN);
            useListener('mousedown', '.resize-handle-n', this.startResizeN);

            useExternalListener(document, 'mousemove', this.resizeS);
            useExternalListener(document, 'mouseup', this.endResizeS);
            useListener('mousedown', '.resize-handle-s', this.startResizeS);

            useExternalListener(document, 'mousemove', this.resizeW);
            useExternalListener(document, 'mouseup', this.endResizeW);
            useListener('mousedown', '.resize-handle-w', this.startResizeW);

            useExternalListener(document, 'mousemove', this.resizeE);
            useExternalListener(document, 'mouseup', this.endResizeE);
            useListener('mousedown', '.resize-handle-e', this.startResizeE);

            useExternalListener(document, 'mousemove', this.resizeNW);
            useExternalListener(document, 'mouseup', this.endResizeNW);
            useListener('mousedown', '.resize-handle-nw', this.startResizeNW);

            useExternalListener(document, 'mousemove', this.resizeNE);
            useExternalListener(document, 'mouseup', this.endResizeNE);
            useListener('mousedown', '.resize-handle-ne', this.startResizeNE);

            useExternalListener(document, 'mousemove', this.resizeSW);
            useExternalListener(document, 'mouseup', this.endResizeSW);
            useListener('mousedown', '.resize-handle-sw', this.startResizeSW);

            useExternalListener(document, 'mousemove', this.resizeSE);
            useExternalListener(document, 'mouseup', this.endResizeSE);
            useListener('mousedown', '.resize-handle-se', this.startResizeSE);

            useExternalListener(document, 'touchmove', this.resizeN);
            useExternalListener(document, 'touchend', this.endResizeN);
            useListener('touchstart', '.resize-handle-n', this.startResizeN);

            useExternalListener(document, 'touchmove', this.resizeS);
            useExternalListener(document, 'touchend', this.endResizeS);
            useListener('touchstart', '.resize-handle-s', this.startResizeS);

            useExternalListener(document, 'touchmove', this.resizeW);
            useExternalListener(document, 'touchend', this.endResizeW);
            useListener('touchstart', '.resize-handle-w', this.startResizeW);

            useExternalListener(document, 'touchmove', this.resizeE);
            useExternalListener(document, 'touchend', this.endResizeE);
            useListener('touchstart', '.resize-handle-e', this.startResizeE);

            useExternalListener(document, 'touchmove', this.resizeNW);
            useExternalListener(document, 'touchend', this.endResizeNW);
            useListener('touchstart', '.resize-handle-nw', this.startResizeNW);

            useExternalListener(document, 'touchmove', this.resizeNE);
            useExternalListener(document, 'touchend', this.endResizeNE);
            useListener('touchstart', '.resize-handle-ne', this.startResizeNE);

            useExternalListener(document, 'touchmove', this.resizeSW);
            useExternalListener(document, 'touchend', this.endResizeSW);
            useListener('touchstart', '.resize-handle-sw', this.startResizeSW);

            useExternalListener(document, 'touchmove', this.resizeSE);
            useExternalListener(document, 'touchend', this.endResizeSE);
            useListener('touchstart', '.resize-handle-se', this.startResizeSE);

            this.size = { height: 0, width: 0 };
            this.loc = { top: 0, left: 0 };
            this.tempSize = {};
        }
        mounted() {
            this.limitArea = this.props.limitArea
                ? document.querySelector(this.props.limitArea)
                : this.el.offsetParent;
            this.limitAreaBoundingRect = this.limitArea.getBoundingClientRect();
            if (this.limitArea === this.el.offsetParent) {
                this.limitLeft = 0;
                this.limitTop = 0;
                this.limitRight = this.limitAreaBoundingRect.width;
                this.limitBottom = this.limitAreaBoundingRect.height;
            } else {
                this.limitLeft = -this.el.offsetParent.offsetLeft;
                this.limitTop = -this.el.offsetParent.offsetTop;
                this.limitRight =
                    this.limitAreaBoundingRect.width - this.el.offsetParent.offsetLeft;
                this.limitBottom =
                    this.limitAreaBoundingRect.height - this.el.offsetParent.offsetTop;
            }
            this.limitAreaWidth = this.limitAreaBoundingRect.width;
            this.limitAreaHeight = this.limitAreaBoundingRect.height;
        }
        startResizeN(event) {
            let realEvent;
            if (event instanceof CustomEvent) {
                realEvent = event.detail;
            } else {
                realEvent = event;
            }
            const { y } = this._getEventLoc(realEvent);
            this.isResizingN = true;
            this.startY = y;
            this.size.height = this.el.offsetHeight;
            this.loc.top = this.el.offsetTop;
            event.stopPropagation();
        }
        resizeN(event) {
            if (this.isResizingN) {
                const { y: newY } = this._getEventLoc(event);
                let dY = newY - this.startY;
                if (dY < 0 && Math.abs(dY) > this.loc.top) {
                    dY = -this.loc.top;
                } else if (dY > 0 && dY > this.size.height) {
                    dY = this.size.height;
                }
                this.el.style.height = `${this.size.height - dY}px`;
                this.el.style.top = `${this.loc.top + dY}px`;
            }
        }
        endResizeN() {
            if (this.isResizingN && !this.isResizingE && !this.isResizingW && !this.isResizingS) {
                this.isResizingN = false;
                this._triggerResizeEnd();
            }
        }
        startResizeS(event) {
            let realEvent;
            if (event instanceof CustomEvent) {
                realEvent = event.detail;
            } else {
                realEvent = event;
            }
            const { y } = this._getEventLoc(realEvent);
            this.isResizingS = true;
            this.startY = y;
            this.size.height = this.el.offsetHeight;
            this.loc.top = this.el.offsetTop;
            event.stopPropagation();
        }
        resizeS(event) {
            if (this.isResizingS) {
                const { y: newY } = this._getEventLoc(event);
                let dY = newY - this.startY;
                if (dY > 0 && dY > this.limitAreaHeight - (this.size.height + this.loc.top)) {
                    dY = this.limitAreaHeight - (this.size.height + this.loc.top);
                } else if (dY < 0 && Math.abs(dY) > this.size.height) {
                    dY = -this.size.height;
                }
                this.el.style.height = `${this.size.height + dY}px`;
            }
        }
        endResizeS() {
            if (!this.isResizingN && !this.isResizingE && !this.isResizingW && this.isResizingS) {
                this.isResizingS = false;
                this._triggerResizeEnd();
            }
        }
        startResizeW(event) {
            let realEvent;
            if (event instanceof CustomEvent) {
                realEvent = event.detail;
            } else {
                realEvent = event;
            }
            const { x } = this._getEventLoc(realEvent);
            this.isResizingW = true;
            this.startX = x;
            this.size.width = this.el.offsetWidth;
            this.loc.left = this.el.offsetLeft;
            event.stopPropagation();
        }
        resizeW(event) {
            if (this.isResizingW) {
                const { x: newX } = this._getEventLoc(event);
                let dX = newX - this.startX;
                if (dX > 0 && dX > this.size.width) {
                    dX = this.size.width;
                } else if (dX < 0 && Math.abs(dX) > this.loc.left + Math.abs(this.limitLeft)) {
                    dX = -this.loc.left + this.limitLeft;
                }
                this.el.style.width = `${this.size.width - dX}px`;
                this.el.style.left = `${this.loc.left + dX}px`;
            }
        }
        endResizeW() {
            if (!this.isResizingN && !this.isResizingE && this.isResizingW && !this.isResizingS) {
                this.isResizingW = false;
                this._triggerResizeEnd();
            }
        }
        startResizeE(event) {
            let realEvent;
            if (event instanceof CustomEvent) {
                realEvent = event.detail;
            } else {
                realEvent = event;
            }
            const { x } = this._getEventLoc(realEvent);
            this.isResizingE = true;
            this.startX = x;
            this.size.width = this.el.offsetWidth;
            this.loc.left = this.el.offsetLeft;
            event.stopPropagation();
        }
        resizeE(event) {
            if (this.isResizingE) {
                const { x: newX } = this._getEventLoc(event);
                let dX = newX - this.startX;
                if (
                    dX > 0 &&
                    dX >
                        this.limitAreaWidth -
                            (this.size.width + this.loc.left + Math.abs(this.limitLeft))
                ) {
                    dX =
                        this.limitAreaWidth -
                        (this.size.width + this.loc.left + Math.abs(this.limitLeft));
                } else if (dX < 0 && Math.abs(dX) > this.size.width) {
                    dX = -this.size.width;
                }
                this.el.style.width = `${this.size.width + dX}px`;
            }
        }
        endResizeE() {
            if (!this.isResizingN && this.isResizingE && !this.isResizingW && !this.isResizingS) {
                this.isResizingE = false;
                this._triggerResizeEnd();
            }
        }
        startResizeNW(event) {
            this.startResizeN(event);
            this.startResizeW(event);
        }
        resizeNW(event) {
            this.resizeN(event);
            this.resizeW(event);
        }
        endResizeNW() {
            if (this.isResizingN && !this.isResizingE && this.isResizingW && !this.isResizingS) {
                this.isResizingN = false;
                this.isResizingW = false;
                this._triggerResizeEnd();
            }
        }
        startResizeNE(event) {
            this.startResizeN(event);
            this.startResizeE(event);
        }
        resizeNE(event) {
            this.resizeN(event);
            this.resizeE(event);
        }
        endResizeNE() {
            if (this.isResizingN && this.isResizingE && !this.isResizingW && !this.isResizingS) {
                this.isResizingN = false;
                this.isResizingE = false;
                this._triggerResizeEnd();
            }
        }
        startResizeSE(event) {
            this.startResizeS(event);
            this.startResizeE(event);
        }
        resizeSE(event) {
            this.resizeS(event);
            this.resizeE(event);
        }
        endResizeSE() {
            if (!this.isResizingN && this.isResizingE && !this.isResizingW && this.isResizingS) {
                this.isResizingS = false;
                this.isResizingE = false;
                this._triggerResizeEnd();
            }
        }
        startResizeSW(event) {
            this.startResizeS(event);
            this.startResizeW(event);
        }
        resizeSW(event) {
            this.resizeS(event);
            this.resizeW(event);
        }
        endResizeSW() {
            if (!this.isResizingN && !this.isResizingE && this.isResizingW && this.isResizingS) {
                this.isResizingS = false;
                this.isResizingW = false;
                this._triggerResizeEnd();
            }
        }
        _getEventLoc(event) {
            let coordX, coordY;
            if (event.touches && event.touches[0]) {
                coordX = event.touches[0].clientX;
                coordY = event.touches[0].clientY;
            } else {
                coordX = event.clientX;
                coordY = event.clientY;
            }
            return {
                x: coordX,
                y: coordY,
            };
        }
        _triggerResizeEnd() {
            const size = {
                height: this.el.offsetHeight,
                width: this.el.offsetWidth,
            };
            const loc = {
                top: this.el.offsetTop,
                left: this.el.offsetLeft,
            };
            this.trigger('resize-end', { size, loc });
        }
    }
    Resizeable.template = 'Resizeable';

    Registries.Component.add(Resizeable);

    return Resizeable;
});
