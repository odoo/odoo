odoo.define('point_of_sale.Draggable', function(require) {
    'use strict';

    const { useExternalListener } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    /**
     * Wrap an element or a component with { position: absolute } to make it
     * draggable around the screen.
     *
     * e.g.
     * ```
     * <Draggable>
     *   <div class="popup">
     *     <DraggableHandle>
     *       <Header />
     *     </DraggableHandle>
     *   </div>
     *   <div class="popup body">
     *   </div>
     * </Draggable>
     * ```
     *
     * In the above snippet, if the popup div is { position: absolute },
     * then it becomes draggable around the screen if it is dragged thru its
     * Header -- the element inside DraggableHandle.
     *
     * DraggableHandle is basically the handle to hold in order to move the
     * Draggable component around.
     *
     * Without DraggableHandle, the Draggable component can still be moved around
     * by pressing Ctrl key while dragging. Useful when the DraggableHandle gets
     * out of the screen.
     */
    class Draggable extends PosComponent {
        static template = 'Draggable';
        constructor() {
            super(...arguments);
            this.isDragging = false;
            this.dx = 0;
            this.dy = 0;
            this.isDraggingWithCtrlKey = false;
            useListener('start-drag', this.startDrag);
            useListener('mousedown', this.allowDraggingWithCtrlKey);
            useListener('click', this.dontPropagateClickWhenDragging, { capture: true });
            // drag with mouse
            useExternalListener(document, 'mousemove', this.move);
            useExternalListener(document, 'mouseup', this.endDrag);
            // drag with touch
            useExternalListener(document, 'touchmove', this.move);
            useExternalListener(document, 'touchend', this.endDrag);
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
        }
        move(event) {
            if (this.isDragging) {
                var { x: left, y: top } = this._getEventLoc(event);
                this.el.style.left = `${left + this.dx}px`;
                this.el.style.top = `${top + this.dy}px`;
            }
            event.preventDefault();
        }
        endDrag() {
            this.isDragging = false;
        }
        _getEventLoc(event) {
            let coordX, coordY;
            if (event.touches && event.touches[0]) {
                coordX = event.touches[0].screenX;
                coordY = event.touches[0].screenY;
            } else {
                coordX = event.screenX;
                coordY = event.screenY;
            }
            return {
                x: coordX,
                y: coordY,
            };
        }
        allowDraggingWithCtrlKey(event) {
            if (event.ctrlKey) {
                this.isDraggingWithCtrlKey = true;
                this.trigger('start-drag', event);
            }
        }
        dontPropagateClickWhenDragging(event) {
            if (this.isDraggingWithCtrlKey) {
                this.isDraggingWithCtrlKey = false;
                event.stopPropagation();
            }
        }
    }

    Registry.add('Draggable', Draggable);

    return { Draggable };
});
