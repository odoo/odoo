export class EventBus extends EventTarget {
    trigger(name, payload) {
        this.dispatchEvent(new CustomEvent(name, { detail: payload }));
    }
}

/**
 * Performs a basic check to make sure a link's protocol is http(s), mainly to
 * deny `javascript:` URLs.
 *
 * @param {string} link
 * @returns {URL|""} URL if the protocol is http(s), empty string otherwise
 */
export function verifyHttpsUrl(link) {
    const url = new URL(link, window.location.href);
    if (!/https?:/.test(url.protocol)) {
        return "";
    }
    return url;
}
