/** @odoo-module **/

import { memoize } from "@web/core/utils/functions";

/**
 * Use this function to handle implicit conversion on canvas.toDataURL due to browser incompatibility
 * See {@link https://caniuse.com/mdn-api_htmlcanvaselement_todataurl_type_parameter_webp}
 *
 * @param {HTMLCanvasElement} canvas
 * @param {string} mimetype See {@link HTMLCanvasElement.toDataURL}
 * @param {number} quality See {@link HTMLCanvasElement.toDataURL}
 * @returns {{dataURL: string, mimetype: string}} The resulting data url from {@link HTMLCanvasElement.toDataURL} and
 * the actual output mimetype
 */
export function convertCanvasToDataURL(canvas, mimetype, quality) {
    const dataURL = canvas.toDataURL(mimetype, quality);
    const actualMimetype = dataURL.split(":")[1].split(";")[0];
    return {
        dataURL,
        mimetype: actualMimetype,
    };
}

/**
 * Checks whether the browser can export a webp image from a canvas using {@link HTMLCanvasElement.toDataURL}
 *
 * @type {() => boolean}
 */
export const canExportCanvasAsWebp = memoize(() => {
    const dummyCanvas = document.createElement("canvas");
    dummyCanvas.width = 1;
    dummyCanvas.height = 1;
    const data = dummyCanvas.toDataURL("image/webp");
    dummyCanvas.remove();
    return data.split(":")[1].split(";")[0] === "image/webp";
});
