import { onMounted, onWillUnmount, useRef } from "@odoo/owl";

export const useStickyTitleObserver = (name, callback) => {
    const ref = useRef(name);
    let observer;

    onMounted(() => {
        if (!ref?.el) {
            return;
        }

        observer = new IntersectionObserver(([entry]) => callback(!entry.isIntersecting), {
            threshold: 0,
        });

        observer.observe(ref.el);
    });

    onWillUnmount(() => {
        if (observer && ref?.el) {
            observer.unobserve(ref.el);
        }
    });
};
