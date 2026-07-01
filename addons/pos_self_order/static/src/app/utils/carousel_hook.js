/* global Carousel */

import { onMounted, onWillUnmount } from "@odoo/owl";
import { session } from "@web/session";
import { resolveRefEl } from "@web/core/utils/ref_utils";

/**
 * Hook to automatically cycle through carousel media (images and videos).
 * - Images move to the next slide after a fixed interval (`timeIntervalSec`).
 * - Videos play from the beginning and switch to the next slide
 *   after their full duration.
 *
 * @param {() => HTMLElement | null} carouselRef - Owl 3 signal ref to the carousel element
 * @param {number} [timeIntervalSec=5]
 */
export function useCarousel(carouselRef, timeIntervalSec = 5) {
    let carousel;
    let timeoutId;

    const getEl = () => resolveRefEl(carouselRef);

    const _clearTimeout = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
    };

    const _waitForVideoMetadata = (video) =>
        new Promise((resolve) => {
            video.addEventListener("loadedmetadata", resolve, { once: true });
        });

    const _getIntervalTime = async () => {
        const activeElement = carousel._activeElement ?? carousel._getItems()[0];
        const video = activeElement?.querySelector("video");
        if (!video) {
            return timeIntervalSec * 1000;
        }
        video.currentTime = 0;
        if (isNaN(video.duration)) {
            // wait for video metadata to loaded
            await _waitForVideoMetadata(video);
        }
        return video.duration * 1000;
    };

    const scheduleNextSlide = async () => {
        _clearTimeout();
        const delay = session.test_mode ? 100 : await _getIntervalTime();
        timeoutId = setTimeout(() => carousel.next(), delay);
    };

    onMounted(() => {
        const el = getEl();
        carousel = new Carousel(el);
        el.addEventListener("slid.bs.carousel", scheduleNextSlide);
        setTimeout(scheduleNextSlide, 100);
    });

    onWillUnmount(() => {
        _clearTimeout();
        getEl()?.removeEventListener("slid.bs.carousel", scheduleNextSlide);
    });
}
