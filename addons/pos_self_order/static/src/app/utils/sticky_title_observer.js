import { onMounted, onWillUnmount } from "@odoo/owl";

export const useStickyTitleObserver = (refSignal, callback) => {
    let observer;

    onMounted(() => {
        const el = refSignal();
        if (!el) {
            return;
        }

        observer = new IntersectionObserver(([entry]) => callback(!entry.isIntersecting), {
            threshold: 0,
        });

        observer.observe(el);
    });

    onWillUnmount(() => {
        const el = refSignal();
        if (observer && el) {
            observer.unobserve(el);
        }
    });
};
