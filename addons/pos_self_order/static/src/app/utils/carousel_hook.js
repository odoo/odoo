/* global Carousel */

import { onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { session } from "@web/session";

/**
 * Hook to automatically cycle through carousel media (images and videos).
 * - Images move to the next slide after a fixed interval (`timeIntervalSec`).
 * - Videos play from the beginning and switch to the next slide
 *   after their full duration.
 *
 * @param {string} refName
 * @param {number} [timeIntervalSec=5]
 */
export function useCarousel(refName, timeIntervalSec = 5) {
    const carouselRef = useRef(refName);
    let carousel;
    let timeoutId;

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
        carousel = new Carousel(carouselRef.el);
        carouselRef.el.addEventListener("slid.bs.carousel", scheduleNextSlide);
        setTimeout(scheduleNextSlide, 100);
    });

    onWillUnmount(() => {
        _clearTimeout();
        carouselRef.el?.removeEventListener("slid.bs.carousel", scheduleNextSlide);
    });
}
