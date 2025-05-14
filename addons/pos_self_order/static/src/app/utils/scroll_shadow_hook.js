import { useState, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";

export function useScrollShadow(scrollContainerRef, options = {}) {
    const { threshold = 5 } = options;
    const shadows = useState({ top: 0, bottom: 0 });

    const updateShadows = () => {
        const el = scrollContainerRef.el;
        if (!el) {
            return;
        }
        const { scrollTop, scrollHeight, clientHeight } = el;
        shadows.top = scrollTop > 0 ? 1 : 0;
        shadows.bottom = scrollTop + clientHeight < scrollHeight - threshold ? 1 : 0;
    };

    initScrollShadow(scrollContainerRef, updateShadows, options);
    return shadows;
}

export function useHorizontalScrollShadow(scrollContainerRef, classContainerRef, options = {}) {
    const { threshold = 5 } = options;

    const updateShadows = () => {
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
    };

    initScrollShadow(scrollContainerRef, updateShadows, options);
}

function initScrollShadow(scrollContainerRef, updateFn, options = {}) {
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
        const el = scrollContainerRef.el;
        if (!el) {
            return;
        }
        el.addEventListener("scroll", handleScroll);
        window.addEventListener("resize", debouncedResize);
        updateFn();
    });

    onPatched(updateFn);

    onWillUnmount(() => {
        const el = scrollContainerRef.el;
        if (el) {
            el.removeEventListener("scroll", handleScroll);
        }
        window.removeEventListener("resize", debouncedResize);
    });
}
