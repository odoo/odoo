import { delay } from "@web/core/utils/concurrency";

export function selectLocation(locationName) {
    return {
        content: `Click on location '${locationName}'`,
        trigger: `.o_self_eating_location_box .preset_btn:contains('${locationName}')`,
        run: "click",
    };
}

export function isClosed() {
    return {
        content: `Check if the POS is closed`,
        trigger: `.o-self-closed`,
    };
}

export function isOpened() {
    return {
        content: `Check if the POS is opened`,
        trigger: `body:not(:has(.o-self-closed))`,
    };
}

export function checkLanguageSelected(language) {
    return {
        content: `Check what the current language is`,
        trigger: `.o_self_language_selector:contains("${language}")`,
    };
}

export function checkCountryFlagShown(country_code) {
    return {
        content: `Check what the current flag is`,
        trigger: `.o_self_language_selector > img[src*=${country_code}]`,
    };
}

export function checkCarouselAutoPlaying() {
    return {
        content: `Check that the slideshow is working`,
        trigger: `.carousel-item.active`,
        async run() {
            const firstSlideHtml = document.querySelector(".carousel-item.active")?.outerHTML;
            await delay(150);
            const currentSlideHtml = document.querySelector(".carousel-item.active")?.outerHTML;
            if (firstSlideHtml === currentSlideHtml) {
                throw new Error(
                    "Slideshow is not working. Slide should change in all self ordering mode."
                );
            }
        },
    };
}
