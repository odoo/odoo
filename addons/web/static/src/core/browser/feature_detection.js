// -----------------------------------------------------------------------------
// Feature detection
// -----------------------------------------------------------------------------

/**
 * True if the browser is based on Chromium (Google Chrome, Opera, Edge).
 */
export function isBrowserChrome() {
    return /Chrome/i.test(navigator.userAgent);
}

export function isBrowserFirefox() {
    return /Firefox/i.test(navigator.userAgent);
}

/**
 * True if the browser is Microsoft Edge.
 */
export function isBrowserMicrosoftEdge() {
    return /Edg/i.test(navigator.userAgent);
}

/**
 * true if the browser is based on Safari (Safari, Epiphany)
 *
 * @returns {boolean}
 */
export function isBrowserSafari() {
    return !isBrowserChrome() && navigator.userAgent?.includes("Safari");
}

export function isAndroid() {
    return /Android/i.test(navigator.userAgent);
}

export function isIOS() {
    let isIOSPlatform = false;
    if ("platform" in navigator) {
        isIOSPlatform = navigator.platform === "MacIntel";
    }
    return (
        /(iPad|iPhone|iPod)/i.test(navigator.userAgent) ||
        (isIOSPlatform && maxTouchPoints() > 1)
    );
}

export function isOtherMobileOS() {
    return /(webOS|BlackBerry|Windows Phone)/i.test(navigator.userAgent);
}

export function isMacOS() {
    return /Mac/i.test(navigator.userAgent);
}

export function isMobileOS() {
    return isAndroid() || isIOS() || isOtherMobileOS();
}

export function isIosApp() {
    return /OdooMobile \(iOS\)/i.test(navigator.userAgent);
}

export function isAndroidApp() {
    return /OdooMobile.+Android/i.test(navigator.userAgent);
}

export function isDisplayStandalone() {
    return matchMedia("(display-mode: standalone)").matches;
}

export function hasTouch() {
    return window.ontouchstart !== undefined || matchMedia("(pointer:coarse)").matches;
}

export function maxTouchPoints() {
    return navigator.maxTouchPoints || 1;
}

export function isVirtualKeyboardSupported() {
    return "virtualKeyboard" in navigator;
}
