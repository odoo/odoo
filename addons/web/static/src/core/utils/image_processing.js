/** @odoo-module **/

const IMAGE_MIMETYPE_FILE_EXTENSIONS = {
    "image/bmp": ["bmp"],
    "image/cgm": ["cgm"],
    "image/g3fax": ["g3"],
    "image/gif": ["gif"],
    "image/ief": ["ief"],
    "image/jp2": ["jp2"],
    "image/jpeg": ["jpg", "jpeg", "jpe"],
    "image/pict": ["pict", "pic", "pct"],
    "image/png": ["png"],
    "image/prs.btif": ["btif"],
    "image/svg+xml": ["svg", "svgz"],
    "image/tiff": ["tiff", "tif"],
    "image/vnd.adobe.photoshop": ["psd"],
    "image/vnd.djvu": ["djvu", "djv"],
    "image/vnd.dwg": ["dwg"],
    "image/vnd.dxf": ["dxf"],
    "image/vnd.fastbidsheet": ["fbs"],
    "image/vnd.fpx": ["fpx"],
    "image/vnd.fst": ["fst"],
    "image/vnd.fujixerox.edmics-mmr": ["mmr"],
    "image/vnd.fujixerox.edmics-rlc": ["rlc"],
    "image/vnd.ms-modi": ["mdi"],
    "image/vnd.net-fpx": ["npx"],
    "image/vnd.wap.wbmp": ["wbmp"],
    "image/vnd.xiff": ["xif"],
    "image/webp": ["webp"],
    "image/x-cmu-raster": ["ras"],
    "image/x-cmx": ["cmx"],
    "image/x-freehand": ["fh", "fhc", "fh4", "fh5", "fh7"],
    "image/x-icon": ["ico"],
    "image/x-macpaint": ["pntg", "pnt", "mac"],
    "image/x-pcx": ["pcx"],
    "image/x-portable-anymap": ["pnm"],
    "image/x-portable-bitmap": ["pbm"],
    "image/x-portable-graymap": ["pgm"],
    "image/x-portable-pixmap": ["ppm"],
    "image/x-quicktime": ["qtif", "qti"],
    "image/x-rgb": ["rgb"],
    "image/x-xbitmap": ["xbm"],
    "image/x-xpixmap": ["xpm"],
    "image/x-xwindowdump": ["xwd"],
};
const IMAGE_FILE_EXTENSION_MIMETYPE = Object.fromEntries(
    Object.entries(IMAGE_MIMETYPE_FILE_EXTENSIONS)
        .map(([mimetype, extensions]) => extensions.map((extension) => [extension, mimetype]))
        .flat()
);

/**
 * The return data of {@link convertCanvasToDataURL}.
 *
 * @typedef {Object} ConvertedCanvasImageData
 * @property {string} dataURL The resulting data url from
 * {@link HTMLCanvasElement#toDataURL}.
 * @property {string} mimetype The actual output mimetype.
 * @property {string} base64Part The base64 part of the data url for
 * convenience.
 * @property {string} defaultFileExtension The base64 part of the data url for
 * convenience.
 */

/**
 * Used to handle implicit mimetype conversions, which is when a browser doesn't
 * support a mimetype as an argument of {@link HTMLCanvasElement#toDataURL} and
 * returns a PNG instead. It returns both the dataURL and its mimetype. It also
 * returns pre-processed data about the output image for convenience.
 *
 * See {@link https://caniuse.com/mdn-api_htmlcanvaselement_todataurl_type_parameter_webp}.
 *
 * @param {HTMLCanvasElement} canvas
 * @param {string} [mimetype] See {@link HTMLCanvasElement#toDataURL}.
 * @param {number} [quality] See {@link HTMLCanvasElement#toDataURL}.
 * @returns {ConvertedCanvasImageData}
 */
export function convertCanvasToDataURL(canvas, mimetype, quality) {
    const dataURL = canvas.toDataURL(mimetype, quality);
    const actualMimetype = extractMimetypeFromDataURL(dataURL);
    return {
        dataURL,
        mimetype: actualMimetype,
        base64Part: extractBase64PartFromDataURL(dataURL),
        defaultFileExtension: getDefaultFileExtensionForMimetype(actualMimetype),
    };
}

/**
 * Check whether the current browser has {@link HTMLCanvasElement#toDataURL}
 * with `image/webp` mimetype capability.
 *
 * The result is memoized since the browser cannot gain or lose that capability
 * during a continuous session.
 *
 * @returns {boolean}
 */
export function canExportCanvasAsWebp() {
    if (typeof canExportCanvasAsWebp._canExportCanvasAsWebp === "undefined") {
        const dummyCanvas = document.createElement("canvas");
        dummyCanvas.width = 1;
        dummyCanvas.height = 1;
        const dataURL = dummyCanvas.toDataURL("image/webp");
        dummyCanvas.remove();
        canExportCanvasAsWebp._canExportCanvasAsWebp =
            extractMimetypeFromDataURL(dataURL) === "image/webp";
    }
    return canExportCanvasAsWebp._canExportCanvasAsWebp;
}

/**
 * @param dataURL
 * @return {string} The image mimetype stored in {@link dataURL}.
 */
export function extractMimetypeFromDataURL(dataURL) {
    return dataURL.split(":")[1].split(";")[0];
}

/**
 * @param {string} dataURL
 * @return {string} The base64 part of {@link dataURL}, without the extra
 * starting and ending format bits. This can be useful to optimize storage.
 */
export function extractBase64PartFromDataURL(dataURL) {
    return dataURL.split(",")[1];
}

/**
 * Map mimetype -> file extension.
 * Only supports image mimetypes.
 *
 * @example "image/jpeg" => "jpeg"
 *
 * @param {string} mimetype
 * @return {string}
 * @throws Error An error for unknown mimetypes.
 */
export function getDefaultFileExtensionForMimetype(mimetype) {
    const extensions = IMAGE_MIMETYPE_FILE_EXTENSIONS[mimetype];
    if (!extensions) {
        throw new Error(`No extension mapping for mimetype ${mimetype}`);
    }
    return extensions?.[0];
}

/**
 * Map file extension -> mimetype.
 * Only supports image extensions.
 *
 * @example "jpg" => "image/jpeg"
 *
 * @param {string} extension
 * @return {string}
 * @throws Error An error for unknown file extensions.
 */
export function getMimetypeForFileExtension(extension) {
    const mimetype = IMAGE_FILE_EXTENSION_MIMETYPE[extension];
    if (!mimetype) {
        throw new Error(`No mimetype mapping for extension ${extension}`);
    }
    return mimetype;
}
