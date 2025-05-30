import { useState, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";

export function useScrollShadow(scrollContainerRef, options = {}) {
    if (!scrollContainerRef) {
        return;
    }

    const { threshold = 5 } = options;
    const shadows = useState({ top: 0, bottom: 0 });

    const updateShadows = () => {
        try {
            const el = scrollContainerRef.el;
            if (!el) {
                return;
            }
            const { scrollTop, scrollHeight, clientHeight } = el;
            shadows.top = scrollTop > 0;
            shadows.bottom = scrollTop + clientHeight < scrollHeight - threshold;
        } catch {
            // Ignore error
        }
    };

    initScrollShadow(scrollContainerRef, updateShadows, options);
    return shadows;
}

export function useHorizontalScrollShadow(scrollContainerRef, classContainerRef, options = {}) {
    if (!scrollContainerRef || !classContainerRef) {
        return;
    }
    const { threshold = 5 } = options;

    const updateShadows = () => {
        try {
            const scrollEl = scrollContainerRef.el;
            const classEl = classContainerRef.el;

            if (!scrollEl || !classEl) {
                return;
            }
            const hasLeft = scrollEl.scrollLeft > 0;
            const hasRight =
                scrollEl.scrollLeft + scrollEl.clientWidth < scrollEl.scrollWidth - threshold;
            classEl.classList.toggle("left-shadow", hasLeft);
            classEl.classList.toggle("right-shadow", hasRight);
            classEl.classList.toggle("has-scroll", scrollEl.clientWidth < scrollEl.scrollWidth);
        } catch {
            // Ignore error
        }
    };

    initScrollShadow(scrollContainerRef, updateShadows, options);
}

function initScrollShadow(scrollContainerRef, updateFn, options = {}) {
    if (!scrollContainerRef) {
        return;
    }
    const { resizeDebounce = 100 } = options;
    let scheduled = false;

    const handleScroll = () => {
        if (!scheduled) {
            scheduled = true;
            requestAnimationFrame(() => {
                scheduled = false;
                updateFn();
            });
        }
    };

    const debouncedResize = debounce(handleScroll, resizeDebounce);

    onMounted(() => {
        try {
            const el = scrollContainerRef.el;
            if (!el) {
                return;
            }
            el.addEventListener("scroll", handleScroll);
            window.addEventListener("resize", debouncedResize);
            updateFn();
        } catch {
            // Ignore error
        }
    });

    onPatched(updateFn);

    onWillUnmount(() => {
        try {
            scrollContainerRef.el?.removeEventListener("scroll", handleScroll);
            window.removeEventListener("resize", debouncedResize);
        } catch {
            // Ignore error
        }
    });
}
