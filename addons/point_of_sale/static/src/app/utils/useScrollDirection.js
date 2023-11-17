/** @odoo-module */

import { useEffect, useState, useRef } from "@odoo/owl";

export function useScrollDirection(refName, cb) {
    const scroll = useState({ down: false });
    const ref = useRef(refName);
    useEffect(
        (element) => {
            if (!element) {
                return;
            }
            const threshold = 60;
            let lastScrollY = element.scrollTop;
            let ticking = false;
            const updateScrollDir = () => {
                const scrollY = element.scrollTop;
                const amountScrolled = Math.abs(scrollY - lastScrollY);
                if (amountScrolled < threshold) {
                    ticking = false;
                    return;
                }
                const scrollingDown = scrollY > lastScrollY;
                if (scrollingDown != scroll.down) {
                    scroll.down = scrollingDown;
                }
                lastScrollY = scrollY;
                ticking = false;
                cb && cb(scroll);
            };

            const onScroll = () => {
                if (!ticking) {
                    window.requestAnimationFrame(updateScrollDir);
                    ticking = true;
                }
            };
            element.addEventListener("scroll", onScroll);
            return () => element.removeEventListener("scroll", onScroll);
        },
        () => [ref.el]
    );

    return scroll;
}
