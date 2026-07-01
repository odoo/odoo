import { onMounted, onWillUnmount } from "@odoo/owl";

import { resolveRefEl } from "@web/core/utils/ref_utils";

export const useStickyTitleObserver = (ref, callback) => {
    let observer;

    const getEl = () => resolveRefEl(ref);

    onMounted(() => {
        const el = getEl();
        if (!el) {
            return;
        }

        observer = new IntersectionObserver(([entry]) => callback(!entry.isIntersecting), {
            threshold: 0,
        });

        observer.observe(el);
    });

    onWillUnmount(() => {
        const el = getEl();
        if (observer && el) {
            observer.unobserve(el);
        }
    });
};
