odoo.define('point_of_sale.Draggable', function(require) {
    'use strict';

    const { useExternalListener } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * Wrap an element or a component with { position: absolute } to make it
     * draggable around the limitArea or the nearest positioned ancestor.
     *
     * e.g.
     * ```
     * <div class="limit-area">
     *   <Draggable limitArea="'.limit-area'">
     *     <div class="popup">
     *       <header class="drag-handle"></header>
     *     </div>
     *     <div class="popup body"></div>
     *   </Draggable>
     * </div>
     * ```
     *
     * In the above snippet, if the popup div is { position: absolute },
     * then it becomes draggable around the .limit-area element if it is dragged
     * thru its Header -- because of the .drag-handle element.
     *
     * @trigger 'drag-end' when dragging ended with payload `{ loc: { top, left } }`
     */
    class Draggable extends PosComponent {
        constructor() {
            super(...arguments);
            this.isDragging = false;
            this.dx = 0;
            this.dy = 0;
            // drag with mouse
            useExternalListener(document, 'mousemove', this.move);
            useExternalListener(document, 'mouseup', this.endDrag);
            // drag with touch
            useExternalListener(document, 'touchmove', this.move);
            useExternalListener(document, 'touchend', this.endDrag);

            useListener('mousedown', '.drag-handle', this.startDrag);
            useListener('touchstart', '.drag-handle', this.startDrag);
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

            // absolutely position the element then remove the transform.
            const elBoundingRect = this.el.getBoundingClientRect();
            this.el.style.top = `${elBoundingRect.top}px`;
            this.el.style.left = `${elBoundingRect.left}px`;
            this.el.style.transform = 'none';
        }
        startDrag(event) {
            let realEvent;
            if (event instanceof CustomEvent) {
                realEvent = event.detail;
            } else {
                realEvent = event;
            }
            const { x, y } = this._getEventLoc(realEvent);
            this.isDragging = true;
            this.dx = this.el.offsetLeft - x;
            this.dy = this.el.offsetTop - y;
            event.stopPropagation();
        }
        move(event) {
            if (this.isDragging) {
                const { x: pointerX, y: pointerY } = this._getEventLoc(event);
                const posLeft = this._getPosLeft(pointerX, this.dx);
                const posTop = this._getPosTop(pointerY, this.dy);
                this.el.style.left = `${posLeft}px`;
                this.el.style.top = `${posTop}px`;
            }
        }
        endDrag() {
            if (this.isDragging) {
                this.isDragging = false;
                this.trigger('drag-end', {
                    loc: { top: this.el.offsetTop, left: this.el.offsetLeft },
                });
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
        _getPosLeft(pointerX, dx) {
            const posLeft = pointerX + dx;
            if (posLeft < this.limitLeft) {
                return this.limitLeft;
            } else if (posLeft > this.limitRight - this.el.offsetWidth) {
                return this.limitRight - this.el.offsetWidth;
            }
            return posLeft;
        }
        _getPosTop(pointerY, dy) {
            const posTop = pointerY + dy;
            if (posTop < this.limitTop) {
                return this.limitTop;
            } else if (posTop > this.limitBottom - this.el.offsetHeight) {
                return this.limitBottom - this.el.offsetHeight;
            }
            return posTop;
        }
    }
    Draggable.template = 'Draggable';

    Registries.Component.add(Draggable);

    return Draggable;
});
