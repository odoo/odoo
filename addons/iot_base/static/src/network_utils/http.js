import { browser } from "@web/core/browser/browser";

/**
 * Format the endpoint to send the request to
 * Used to ensure the request is sent with the same protocol as the current page
 * (e.g. if the current page is HTTPS, the request will be sent to the IoT Box using HTTPS)
 * @param {string} ip IP Address of the IoT Box
 * @param {string} route Route to send the request to
 * @param {boolean} forceHttp If true, always use HTTP even in HTTPS context (for browser supporting LNA)
 * @returns {string} The formatted endpoint
 */
export function formatEndpoint(ip, route, forceHttp = false) {
    const protocol = forceHttp ? "http:" : window.location.protocol;
    const rawIp = forceHttp ? ip.replace(/^(\d+)-(\d+)-(\d+)-(\d+).*/, "$1.$2.$3.$4") : ip;
    const url = new URL(`${protocol}//${rawIp}`);
    url.pathname = route;
    return url.toString();
}

/**
 * Send a POST request to the IoT Box
 * @param {string} ip IP Address of the IoT Box
 * @param {string} route Endpoint to send the request to
 * @param {Record<string, unknown>} params Parameters to send with the request (optional)
 * @param {number} timeout Time before the request times out (default: 6000ms)
 * @param {Record<string, unknown>} headers HTTP headers to send with the request (optional)
 * @param {AbortSignal} abortSignal AbortSignal used to cancel the request early (optional)
 * @param {boolean} useLna If true, use local targetAddressSpace + Force HTTP
 * @returns {Promise<any>}
 */
export async function post(ip, route, params = {}, timeout = 6000, headers = {}, abortSignal = null, useLna = false) {
    const endpoint = formatEndpoint(ip, route, useLna);
    const timeoutSignal = AbortSignal.timeout(timeout);
    const response = await browser.fetch(endpoint, {
        body: JSON.stringify({'params': params}),
        method: "POST",
        headers: {"Content-Type": "application/json", ...headers},
        signal: abortSignal ? AbortSignal.any([abortSignal, timeoutSignal]) : timeoutSignal,
        targetAddressSpace: useLna ? "local" : undefined,
    });

    return response.json();
}
