export function selectLocation(locationName) {
    return {
        content: `Click on location '${locationName}'`,
        trigger: `.o_self_eating_location span:contains('${locationName}')`,
        run: "click",
    };
}

export function selectKioskLocation(locationName) {
    return {
        content: `Click on location '${locationName}'`,
        trigger: `.o_kiosk_eating_location_box .preset_btn:contains('${locationName}')`,
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
        trigger: `.self_order_language_selector:contains("${language}")`,
    };
}

export function checkCountryFlagShown(country_code) {
    return {
        content: `Check what the current flag is`,
        trigger: `.self_order_language_selector > img[src*=${country_code}]`,
    };
}

export function checkKioskLanguageSelected(language) {
    return {
        content: `Check what the current language is`,
        trigger: `.o_kiosk_language_selector:contains("${language}")`,
    };
}

export function checkKioskCountryFlagShown(country_code) {
    return {
        content: `Check what the current flag is`,
        trigger: `.o_kiosk_language_selector > img[src*=${country_code}]`,
    };
}
