/* global Carousel */

import { onMounted, onWillUnmount, usePlugin } from "@odoo/owl";
import { session } from "@web/session";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

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
    const bootstrap = usePlugin(BootstrapInstance);
    let carousel;
    let timeoutId;
    let unmounted = false;

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
        if (unmounted) {
            // `_getIntervalTime` awaits the active video's metadata, so the
            // page can be gone - and `carousel` disposed - by now. `next()`
            // on a disposed instance reaches
            // `Element.prototype.querySelector.call(null, ...)`.
            return;
        }
        timeoutId = setTimeout(() => carousel.next(), delay);
    };

    const _dropCallbacksOnceDisposed = (instance) => {
        if (Object.hasOwn(instance, "_queueCallback")) {
            return;
        }
        const queueCallback = instance._queueCallback;
        instance._queueCallback = function (callback, ...args) {
            // `_element` is the liveness sentinel: set in the constructor,
            // nulled by `dispose()`.
            return queueCallback.call(this, () => this._element && callback(), ...args);
        };
    };

    onMounted(() => {
        const el = carouselRef();
        carousel = bootstrap.getOrCreateInstance(Carousel, el);
        _dropCallbacksOnceDisposed(carousel);
        el.addEventListener("slid.bs.carousel", scheduleNextSlide);
        timeoutId = setTimeout(scheduleNextSlide, 100);
    });

    onWillUnmount(() => {
        unmounted = true;
        _clearTimeout();
        carouselRef()?.removeEventListener("slid.bs.carousel", scheduleNextSlide);
    });
}
