/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

// =============================================================================
// 1. UTILITIES & HELPERS
// =============================================================================

/**
 * Secure UUID Generator.
 * Uses `crypto.randomUUID` if available; falls back to a polyfill for older environments.
 * Used for tracing requests via Correlation IDs.
 */
const generateUUID = () => {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
};

/**
 * Advanced Query Parameter Serializer.
 * Handles nested objects, arrays, and Dates recursively.
 * Includes protection against circular references and infinite recursion depth.
 * * @param {Object} obj - The parameters to serialize.
 * @param {String} [prefix] - Internal use for recursion.
 * @param {WeakSet} [visited] - Internal use for circular reference detection.
 * @returns {String} URL encoded query string.
 */
function serializeParams(obj, prefix, visited = new WeakSet()) {
    const str = [];
    const MAX_DEPTH = 5; // Guard against stack overflow
    
    // Depth check to prevent infinite recursion on deeply nested objects
    if (prefix && prefix.split('[').length > MAX_DEPTH) return []; 

    for (const p in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, p)) {
            const k = prefix ? `${prefix}[${p}]` : p;
            const v = obj[p];

            if (v === null || v === undefined) continue;

            if (typeof v === 'object') {
                if (visited.has(v)) continue; // Skip circular references
                visited.add(v);

                if (Array.isArray(v)) {
                    // Standard array serialization: key[]=val1&key[]=val2
                    v.forEach(item => {
                        if (typeof item === 'object') {
                             str.push(serializeParams(item, `${k}[]`, visited));
                        } else {
                             str.push(encodeURIComponent(`${k}[]`) + "=" + encodeURIComponent(item));
                        }
                    });
                } else if (v instanceof Date) {
                    str.push(encodeURIComponent(k) + "=" + encodeURIComponent(v.toISOString()));
                } else {
                    str.push(serializeParams(v, k, visited));
                }
            } else {
                str.push(encodeURIComponent(k) + "=" + encodeURIComponent(v));
            }
        }
    }
    return str.flat().join("&");
}

/**
 * Abort-Aware Delay Promise.
 * Resolves after `ms` milliseconds, but rejects immediately if the `signal` is aborted.
 * Crucial for preventing memory leaks when components are unmounted during a retry wait.
 */
function abortableDelay(ms, signal) {
    return new Promise((resolve, reject) => {
        if (signal?.aborted) return reject(new DOMException('Aborted', 'AbortError'));
        
        const timer = browser.setTimeout(() => resolve(true), ms);
        
        signal?.addEventListener('abort', () => {
            browser.clearTimeout(timer);
            reject(new DOMException('Aborted', 'AbortError'));
        }, { once: true });
    });
}

/**
 * Parses the `Retry-After` header.
 * Supports both integer (seconds) and HTTP-Date formats as per RFC 7231.
 */
function parseRetryAfter(headerValue) {
    if (!headerValue) return 0;
    
    // 1. Try parsing as seconds
    const seconds = parseInt(headerValue, 10);
    if (!isNaN(seconds)) return seconds * 1000;

    // 2. Try parsing as HTTP Date
    const date = Date.parse(headerValue);
    if (!isNaN(date)) {
        return Math.max(0, date - Date.now());
    }
    
    return 0;
}

// =============================================================================
// 2. ERROR HANDLING & OBSERVABILITY
// =============================================================================

/**
 * Enhanced Error Class for HTTP failures.
 * Carries contextual information (status, headers, latency) to aid debugging and telemetry.
 */
class HttpError extends Error {
    constructor(message, context) {
        super(message);
        this.name = "HttpError";
        this.status = context.status;
        this.url = context.url;
        this.method = context.method;
        this.body = context.body;
        this.headers = context.headers;
        
        // Metrics for observability
        this.metrics = {
            totalLatency: context.totalLatency,
            attemptLatency: context.attemptLatency,
            attempts: context.attempts
        };
        this.correlationId = context.correlationId;
        this.timestamp = new Date().toISOString();
    }
}

// =============================================================================
// 3. CORE SERVICE ARCHITECTURE
// =============================================================================

class HttpService {
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || "";
        this.defaultTimeout = config.timeout || 10000;
        
        // Defensive wrapper for the logger to ensure safety if a custom logger is missing methods
        this.logger = {
            info: (msg, meta) => config.logger?.info?.(msg, meta),
            warn: (msg, meta) => config.logger?.warn?.(msg, meta),
            error: (msg, meta) => config.logger?.error?.(msg, meta),
        };
        
        this.defaultHeaders = config.defaultHeaders || {};
        this.interceptors = { request: [], response: [] };
    }

    useRequestInterceptor(fn) { this.interceptors.request.push(fn); }
    useResponseInterceptor(fn) { this.interceptors.response.push(fn); }

    /**
     * Determines whether a failed request should be retried.
     * Enforces strict idempotency rules to prevent data duplication on non-safe methods (like POST).
     */
    _shouldRetry(error, attempt, maxRetries, method, allowNonIdempotent) {
        if (attempt >= maxRetries) return false;
        
        // 1. Fatal Errors: Never retry (User Abort, Auth Failure, 404 Not Found)
        if (error.name === "AbortError") return false; 
        if (error.status === 401 || error.status === 403) return false;
        if (error.status === 404) return false;

        // 2. Idempotency Check:
        // Methods like POST/PATCH are not idempotent. Retrying them blindly can cause
        // duplicate records (e.g., double payments). We only retry them if explicitly allowed.
        const isIdempotent = ["GET", "PUT", "DELETE", "HEAD", "OPTIONS"].includes(method.toUpperCase());
        
        if (!isIdempotent && !allowNonIdempotent) {
            return false;
        }

        // 3. Retry Candidates:
        // - Network failures (status is undefined/null)
        // - Rate Limits (429)
        // - Service Unavailable / Gateway Timeout (5xx)
        if (!error.status) return true;
        if (error.status === 429 || error.status === 503) return true;
        if (error.status >= 500 && error.status <= 599) return true;

        return false;
    }

    async _request(endpoint, options = {}) {
        const globalStartTime = Date.now();
        const correlationId = options.correlationId || generateUUID();
        
        // Create an immutable configuration snapshot for this request lifecycle
        const config = {
            method: (options.method || "GET").toUpperCase(),
            headers: { ...this.defaultHeaders, ...options.headers },
            body: options.body,
            params: options.params,
            timeout: options.timeout || this.defaultTimeout,
            retries: options.retries ?? 0, 
            responseType: options.responseType, // 'json' | 'text' | 'blob' | undefined
            allowNonIdempotentRetry: options.allowNonIdempotentRetry || false,
        };

        let url = `${this.baseUrl}${endpoint}`;
        if (config.params) {
            const qs = serializeParams(config.params);
            url += (url.includes("?") ? "&" : "?") + qs;
        }

        let attempt = 0;

        // MAIN RETRY LOOP
        // Guaranteed to terminate because attempt increments strictly.
        while (attempt <= config.retries) {
            const attemptStartTime = Date.now();
            const controller = new AbortController();
            
            // Per-attempt timeout logic
            const timeoutId = browser.setTimeout(() => controller.abort(), config.timeout);

            try {
                // 1. RUN REQUEST INTERCEPTORS
                // Critical: Must run on every attempt. If a token expires, the interceptor
                // can refresh it before the next retry.
                let requestConfig = { ...config, url }; 
                
                for (const interceptor of this.interceptors.request) {
                    const modified = await interceptor(requestConfig);
                    if (!modified) throw new Error("Interceptor must return the config object.");
                    requestConfig = modified;
                }

                // Header Normalization & Body Serialization
                const finalHeaders = new Headers(requestConfig.headers);
                if (!finalHeaders.has("X-Correlation-ID")) {
                    finalHeaders.set("X-Correlation-ID", correlationId);
                }

                // Auto-detect JSON body if not explicitly set
                let finalBody = requestConfig.body;
                if (finalBody && !(finalBody instanceof FormData) && 
                    !finalHeaders.has("Content-Type") && 
                    !(finalBody instanceof Blob) && 
                    !(finalBody instanceof ArrayBuffer)) {
                        finalHeaders.set("Content-Type", "application/json");
                        finalBody = JSON.stringify(finalBody);
                }

                // 2. EXECUTE FETCH
                const response = await browser.fetch(requestConfig.url, {
                    method: requestConfig.method,
                    headers: finalHeaders,
                    body: finalBody,
                    signal: controller.signal,
                });

                browser.clearTimeout(timeoutId);

                // 3. RESPONSE PARSING
                // Prioritize the caller's requested type, otherwise sniff Content-Type.
                let data;
                const contentType = response.headers.get("Content-Type") || "";

                if (config.responseType === 'blob') {
                    data = await response.blob();
                } else if (config.responseType === 'text') {
                    data = await response.text();
                } else if (config.responseType === 'json') {
                     data = await response.json();
                } else {
                    // Smart detection: covers 'application/json', 'application/vnd.api+json', etc.
                    if (contentType.match(/^application\/(.*json|vnd\.api\+json)/)) {
                        data = await response.json();
                    } else {
                        data = await response.text();
                    }
                }

                // 4. CHECK STATUS
                if (!response.ok) {
                    throw new HttpError(`HTTP ${response.status}`, {
                        status: response.status,
                        statusText: response.statusText,
                        url: response.url,
                        method: requestConfig.method,
                        headers: response.headers,
                        body: data,
                        correlationId,
                        totalLatency: Date.now() - globalStartTime,
                        attemptLatency: Date.now() - attemptStartTime,
                        attempts: attempt + 1
                    });
                }

                // 5. RUN RESPONSE INTERCEPTORS
                let result = data;
                for (const interceptor of this.interceptors.response) {
                    const modified = await interceptor(result, response);
                    result = modified;
                }

                return result; // Request Successful

            } catch (error) {
                browser.clearTimeout(timeoutId); // Ensure cleanup
                
                // Determine if we should retry based on error type and configuration
                const shouldRetry = this._shouldRetry(error, attempt, config.retries, config.method, config.allowNonIdempotentRetry);

                if (shouldRetry) {
                    attempt++;
                    
                    // Calculate Delay: Prefer 'Retry-After' header, otherwise use Exponential Backoff + Jitter
                    const retryAfterMs = parseRetryAfter(error.headers?.get("Retry-After"));
                    const baseBackoff = Math.min(10000, 500 * (2 ** attempt)); 
                    const jitter = Math.random() * 200;
                    const delay = retryAfterMs > 0 ? retryAfterMs : (baseBackoff + jitter);

                    this.logger.warn(`[HTTP] Retry attempt ${attempt}/${config.retries} for ${url}. Waiting ${delay}ms.`, {
                        correlationId,
                        cause: error.message
                    });

                    // Wait (Abort-safe)
                    // If the component unmounts or user cancels, this will throw and exit the loop.
                    await abortableDelay(delay, options.signal); 
                    
                    continue; // Restart Loop
                }

                // Log final failure with full context for debugging
                this.logger.error(`[HTTP] Failed request to ${url}`, {
                    correlationId,
                    method: config.method,
                    status: error.status,
                    totalLatency: Date.now() - globalStartTime
                });
                
                throw error;
            }
        }
    }

    // Public API Facade
    get(url, params, options) { return this._request(url, { ...options, method: "GET", params }); }
    post(url, data, options) { return this._request(url, { ...options, method: "POST", body: data }); }
    put(url, data, options) { return this._request(url, { ...options, method: "PUT", body: data }); }
    delete(url, options = {}) { return this._request(url, { ...options, method: "DELETE" }); }
}

// =============================================================================
// 4. REGISTRATION & EXPORT
// =============================================================================

// Default configuration (Should be hydrated from environment variables in production)
const serviceConfig = {
    baseUrl: "", 
    timeout: 20000,
    logger: console 
};

export const httpService = new HttpService(serviceConfig);

registry.category("services").add("http", {
    start: () => httpService,
});
