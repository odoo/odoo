import { onMounted, onWillUnmount, signal } from "@odoo/owl";

/**
 * Observe a title element and notify when it leaves or re-enters the viewport.
 * This hook returns a signal ref that should be attached to the title element.
 *
 * @param {Function} callback Function called whenever the
 *   title visibility changes.
 * @returns {signal} Owl signal ref to attach to the observed title element.
 */
export const useStickyTitleObserver = (callback) => {
    const titleRef = signal(null);
    let observer;

    onMounted(() => {
        if (!titleRef()) {
            return;
        }

        observer = new IntersectionObserver(([entry]) => callback(!entry.isIntersecting), {
            threshold: 0,
        });

        observer.observe(titleRef());
    });

    onWillUnmount(() => {
        if (observer && titleRef()) {
            observer.unobserve(titleRef());
        }
    });
    return titleRef;
};
