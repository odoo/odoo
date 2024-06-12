/** @odoo-module **/

import { loadJS } from "../assets"; // use the real, non patched (in tests), loadJS
import { isBrowserChrome } from "../browser/feature_detection";

/** @typedef {import("./error_service").UncaughtError} UncaughtError */

/**
 * @param {UncaughtError} uncaughtError
 * @param {Error} originalError
 * @returns {string}
 */
function combineErrorNames(uncaughtError, originalError) {
    const originalErrorName = getErrorTechnicalName(originalError);
    const uncaughtErrorName = getErrorTechnicalName(uncaughtError);
    if (originalErrorName === Error.name) {
        return uncaughtErrorName;
    } else {
        return `${uncaughtErrorName} > ${originalErrorName}`;
    }
}

/**
 * Returns the full traceback for an error chain based on error causes
 *
 * @param {Error} error
 * @returns {string}
 */
export function fullTraceback(error) {
    let traceback = formatTraceback(error);
    let current = error.cause;
    while (current) {
        traceback += `\n\nCaused by: ${
            current instanceof Error ? formatTraceback(current) : current
        }`;
        current = current.cause;
    }
    return traceback;
}

/**
 * Returns the full annotated traceback for an error chain based on error causes
 *
 * @param {Error} error
 * @returns {Promise<string>}
 */
export async function fullAnnotatedTraceback(error) {
    if (error.annotatedTraceback) {
        return error.annotatedTraceback;
    }
    // If we don't call preventDefault  synchronously while handling the error
    // event, the error will be logged in the console with an unannotated
    // traceback. This is a problem because annotating a traceback cannot be
    // done synchronously. To work around this issue, we always call
    // preventDefault, which means it is never logged but we rethrow the error
    // after annotating its traceback, which will cause the error to be handled
    // again after the traceback has been annotated, and this function will be
    // called again and return synchronously (see above)
    if (error.errorEvent) {
        error.errorEvent.preventDefault();
    }
    let traceback;
    try {
        traceback = await annotateTraceback(error);
        let current = error.cause;
        while (current) {
            traceback += `\n\nCaused by: ${
                current instanceof Error ? await annotateTraceback(current) : current
            }`;
            current = current.cause;
        }
    } catch (e) {
        console.warn("Failed to annotate traceback for error:", error, "failure reason:", e);
        traceback = fullTraceback(error);
    }
    error.annotatedTraceback = traceback;
    if (error.errorEvent) {
        throw error;
    }
    return traceback;
}

/**
 * @param {UncaughtError} uncaughtError
 * @param {Error} originalError
 * @param {boolean} annotated
 * @returns {Promise<void>}
 */
export async function completeUncaughtError(uncaughtError, originalError, annotated = false) {
    uncaughtError.name = combineErrorNames(uncaughtError, originalError);
    if (annotated) {
        uncaughtError.traceback = await fullAnnotatedTraceback(originalError);
    } else {
        uncaughtError.traceback = fullTraceback(originalError);
    }
    if (originalError.message) {
        uncaughtError.message = `${uncaughtError.message} > ${originalError.message}`;
    }
    uncaughtError.cause = originalError;
}

/**
 * @param {Error} error
 * @returns {string}
 */
export function getErrorTechnicalName(error) {
    return error.name !== Error.name ? error.name : error.constructor.name;
}

/**
 * Format the traceback of an error. Basically, we just add the error message
 * in the traceback if necessary (Chrome already does it by default, but not
 * other browser.)
 *
 * @param {Error} error
 * @returns {string}
 */
export function formatTraceback(error) {
    let traceback = error.stack;
    const errorName = getErrorTechnicalName(error);
    if (!isBrowserChrome()) {
        // transforms the stack into a chromium stack by adding the error name
        // to the stack and indenting the lines, eg:
        // Error: Mock: Can't write value
        //     _onOpenFormView@http://localhost:8069/web/content/425-baf33f1/web.assets.js:1064:30
        //     ...
        traceback = `${errorName}: ${error.message}\n${error.stack}`
            .replace(/\n/g, "\n    ")
            .trim();
    } else if (error.stack) {
        // Chromium stack starts with the error's name but the name is "Error" by default
        // so we replace it to have the error type name
        traceback = error.stack.replace(/^[^:]*/g, errorName);
    }
    return traceback;
}

/**
 * Returns an annotated traceback from an error. This is asynchronous because
 * it needs to fetch the sourcemaps for each script involved in the error,
 * then compute the correct file/line numbers and add the information to the
 * correct line.
 *
 * @param {Error} error
 * @returns {Promise<string>}
 */
export async function annotateTraceback(error) {
    const traceback = formatTraceback(error);
    try {
        await loadJS("/web/static/lib/stacktracejs/stacktrace.js");
    } catch {
        return traceback;
    }
    // In Firefox, the error stack generated by anonymous code (example: invalid
    // code in a template) is not compatible with the stacktrace lib. This code
    // corrects the stack to make it compatible with the lib stacktrace.
    if (error.stack) {
        const regex = / line (\d*) > (Function):(\d*)/gm;
        const subst = `:$1`;
        error.stack = error.stack.replace(regex, subst);
    }
    // eslint-disable-next-line no-undef
    let frames;
    try {
        frames = await StackTrace.fromError(error);
    } catch (e) {
        // This can crash if the originalError has no stack/stacktrace property
        console.warn("The following error could not be annotated:", error, e);
        return traceback;
    }
    const lines = traceback.split("\n");
    if (lines[lines.length - 1].trim() === "") {
        // firefox traceback have an empty line at the end
        lines.splice(-1);
    }

    let lineIndex = 0;
    let frameIndex = 0;
    while (frameIndex < frames.length) {
        const line = lines[lineIndex];
        // skip lines that have no location information as they don't correspond to a frame
        if (!line.match(/:\d+:\d+\)?$/)) {
            lineIndex++;
            continue;
        }
        const frame = frames[frameIndex];
        const info = ` (${frame.fileName}:${frame.lineNumber})`;
        lines[lineIndex] = line + info;
        lineIndex++;
        frameIndex++;
    }
    return lines.join("\n");
}
