import { onMounted, onWillUnmount } from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";

export function useDraggableScroll(scrollContainerRef, options = {}) {
    if (hasTouch() || !scrollContainerRef) {
        return;
    }
    const threshold = options.threshold ?? 5;

    // Transitional: Owl 3 native refs are signals (element via calling the ref),
    // while legacy refs expose `.el`. Resolve the element in one place so both work.
    const getScrollEl = () =>
        typeof scrollContainerRef === "function" ? scrollContainerRef() : scrollContainerRef?.el;

    let isDragging = false;
    let dragMoved = false;
    let startX;
    let scrollLeft;
    let shouldSuppressClick = false;
    const onMouseDown = (e) => {
        const scrollEl = getScrollEl();
        if (!scrollEl) {
            return;
        }
        isDragging = true;
        dragMoved = false;
        startX = e.pageX - scrollEl.offsetLeft;
        scrollLeft = scrollEl.scrollLeft;
    };

    const onMouseMove = (e) => {
        const scrollEl = getScrollEl();

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
        const scrollEl = getScrollEl();
        scrollEl?.addEventListener("mousedown", onMouseDown);
        scrollEl?.addEventListener("click", onClick, true);
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    });

    onWillUnmount(() => {
        const scrollEl = getScrollEl();
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
        scrollEl?.removeEventListener("mousedown", onMouseDown);
        scrollEl?.removeEventListener("click", onClick, true);
    });
}
