/**
 * Mixin providing pinch-to-zoom touch gesture methods for the ProductImageViewer.
 */
export const ImageViewerTouchMixin = {
    _getTouchDistance(ev) {
        return Math.hypot(
            ev.touches[0].clientX - ev.touches[1].clientX,
            ev.touches[0].clientY - ev.touches[1].clientY
        );
    },

    _onTouchendImage(ev) {
        if (ev.touches.length === 0) {
            if (this._pendingScale !== undefined) {
                this.state.imageScale = this._pendingScale;
                this._pendingScale = undefined;
                ev.currentTarget.classList.add('transition-base');
                this.initialPinchDistance = null;
            }
            // Delay reset so the ghost click after touchend doesn't trigger drag logic
            setTimeout(() => {
                this.isDragging = false;
            }, 50);
        } else if (ev.touches.length === 1 && this.initialPinchDistance) {
            this.initialPinchDistance = null;
            this.isDragging = false;
        }
    },

    _onTouchstartImage(ev) {
        if (ev.touches.length === 2) {
            this.isDragging = false;
            this.initialPinchDistance = this._getTouchDistance(ev)
            this.initialPinchScale = this.state.imageScale;
            this._pendingScale = this.state.imageScale;
            ev.currentTarget.classList.remove('transition-base');
        } else if (ev.touches.length === 1 && !this.initialPinchDistance) {
            this.isDragging = true;
            this.dragStartPos = {
                x: ev.touches[0].clientX - this.imageTranslate.x,
                y: ev.touches[0].clientY - this.imageTranslate.y,
                clientX: ev.touches[0].clientX,
                clientY: ev.touches[0].clientY,
            };
        }
    },

    _onTouchmoveImage(ev) {
        ev.preventDefault();
        if (ev.touches.length === 2 && this.initialPinchDistance) {
            const currentDist = this._getTouchDistance(ev);
            const newScale = Math.max(0.5, this.initialPinchScale * (currentDist / this.initialPinchDistance));
            this._pendingScale = newScale;
            ev.currentTarget.style.transform = `scale3d(${newScale}, ${newScale}, 1)`;
        } else if (ev.touches.length === 1 && this.isDragging && !this.initialPinchDistance) {
            this.imageTranslate.x = ev.touches[0].clientX - this.dragStartPos.x;
            this.imageTranslate.y = ev.touches[0].clientY - this.dragStartPos.y;
            this.updateImage();
        }
    },
};
