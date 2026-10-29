export const PRINTER_NOT_REACHABLE = "PRINTER_NOT_REACHABLE";

/**
 * Base URL of a printer of the local network.
 *
 * @param {Object} printer
 * @param {string} printer.address host name or IP address, optionally with a
 *   port or a path
 * @returns {string}
 */
export function getPrinterUrl(printer) {
    return `http://${printer.address.trim().replace(/\/+$/, "")}`;
}

/**
 * Send a request to a device of the local network.
 *
 * Browsers implementing Local Network Access only let a page reach the local
 * network, and a secure page send requests over plain HTTP, when the request
 * declares the address space it targets.
 *
 * @param {string} url
 * @param {RequestInit} params
 * @returns {Promise<Response>}
 */
export function fetchLocalNetwork(url, params) {
    const { hostname } = new URL(url);
    const isLoopback = ["localhost", "127.0.0.1", "[::1]"].includes(hostname);
    return fetch(url, { ...params, targetAddressSpace: isLoopback ? "loopback" : "local" });
}
