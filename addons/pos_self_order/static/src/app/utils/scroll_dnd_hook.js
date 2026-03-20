import { onMounted, onWillUnmount } from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";

export function useDraggableScroll(scrollContainerRef, options = {}) {
    if (hasTouch() || !scrollContainerRef) {
        return;
    }
    const threshold = options.threshold ?? 5;

    let isDragging = false;
    let dragMoved = false;
    let startX;
    let scrollLeft;
    let shouldSuppressClick = false;
    const onMouseDown = (e) => {
        const scrollEl = scrollContainerRef.el;
        if (!scrollEl) {
            return;
        }
        isDragging = true;
        dragMoved = false;
        startX = e.pageX - scrollEl.offsetLeft;
        scrollLeft = scrollEl.scrollLeft;
    };

    const onMouseMove = (e) => {
        const scrollEl = scrollContainerRef.el;

        if (!isDragging || !scrollEl) {
            return;
        }

        const x = e.pageX - scrollEl.offsetLeft;
        const walk = x - startX;

        if (Math.abs(walk) > threshold) {
            dragMoved = true;
        }

        e.preventDefault();
        scrollEl.scrollLeft = scrollLeft - walk;
    };

    const onMouseUp = (e) => {
        if (!isDragging) {
            return;
        }
        if (isDragging && dragMoved) {
            shouldSuppressClick = true;
        }
        isDragging = false;
    };

    const onClick = (e) => {
        if (shouldSuppressClick) {
            e.stopPropagation();
            e.preventDefault();
            shouldSuppressClick = false; // reset after one suppression
        }
    };

    onMounted(() => {
        scrollContainerRef.el?.addEventListener("mousedown", onMouseDown);
        scrollContainerRef.el?.addEventListener("click", onClick, true);
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    });

    onWillUnmount(() => {
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        scrollContainerRef.el?.removeEventListener("mousedown", onMouseDown);
        scrollContainerRef.el?.removeEventListener("click", onClick, true);
    });
}
