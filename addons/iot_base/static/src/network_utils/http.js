import { browser } from "@web/core/browser/browser";

/**
 * Format the endpoint to send the request to
 * Used to ensure the request is sent with the same protocol as the current page
 * (e.g. if the current page is HTTPS, the request will be sent to the IoT Box using HTTPS)
 * @param ip IP Address of the IoT Box
 * @param route Route to send the request to
 * @returns {string} The formatted endpoint
 */
export function formatEndpoint(ip, route) {
    const url = new URL(window.location.href);
    url.search = "";
    url.hostname = ip;
    url.pathname = route;
    if (url.port) url.port = "8069";
    return url.toString();
}

/**
 * Send a POST request to the IoT Box
 * @param ip IP Address of the IoT Box
 * @param route Endpoint to send the request to
 * @param params Parameters to send with the request (optional)
 * @param timeout Time before the request times out (default: 6000ms)
 * @param headers HTTP headers to send with the request (optional)
 * @param abortSignal AbortSignal used to cancel the request early (optional)
 * @returns {Promise<any>}
 */
export async function post(ip, route, params = {}, timeout = 6000, headers = {}, abortSignal = null) {
    const endpoint = formatEndpoint(ip, route);
    const timeoutSignal = AbortSignal.timeout(timeout);
    const response = await browser.fetch(endpoint, {
        body: JSON.stringify({'params': params}),
        method: "POST",
        headers: {"Content-Type": "application/json", ...headers},
        signal: abortSignal ? AbortSignal.any([abortSignal, timeoutSignal]) : timeoutSignal,
    });

    return response.json();
}
