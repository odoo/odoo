import { onMounted, onWillUnmount } from "@odoo/owl";

export const useStickyTitleObserver = (ref, callback) => {
    let observer;

    onMounted(() => {
        const el = ref();
        if (!el) {
            return;
        }

        observer = new IntersectionObserver(([entry]) => callback(!entry.isIntersecting), {
            threshold: 0,
        });

        observer.observe(el);
    });

    onWillUnmount(() => {
        const el = ref();
        if (observer && el) {
            observer.unobserve(el);
        }
    });
};
