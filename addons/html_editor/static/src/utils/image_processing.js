import { rpc } from "@web/core/network/rpc";
import { pick } from "@web/core/utils/objects";
import { getAffineApproximation, getProjective } from "./perspective_utils";

// Fields returned by cropperjs 'getData' method, also need to be passed when
// initializing the cropper to reuse the previous crop.
export const cropperDataFields = ["x", "y", "width", "height", "rotate", "scaleX", "scaleY"];
export const isGif = (mimetype) => mimetype === "image/gif";

// webgl color filters
const _applyAll = (result, filter, filters) => {
    filters.forEach((f) => {
        if (f[0] === "blend") {
            const cv = f[1];
            const ctx = result.getContext("2d");
            ctx.globalCompositeOperation = f[2];
            ctx.globalAlpha = f[3];
            ctx.drawImage(cv, 0, 0);
            ctx.globalCompositeOperation = "source-over";
            ctx.globalAlpha = 1.0;
        } else {
            filter.addFilter(...f);
        }
    });
};
let applyAll;

const glFilters = {
    blur: (filter) => filter.addFilter("blur", 10),

    1977: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "rgb(243, 106, 188)";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "screen", 0.3],
            ["brightness", 0.1],
            ["contrast", 0.1],
            ["saturation", 0.3],
        ]);
    },

    aden: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "rgb(66, 10, 14)";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "darken", 0.2],
            ["brightness", 0.2],
            ["contrast", -0.1],
            ["saturation", -0.15],
            ["hue", 20],
        ]);
    },

    brannan: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "rgb(161, 44, 191)";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "lighten", 0.31],
            ["sepia", 0.5],
            ["contrast", 0.4],
        ]);
    },

    earlybird: (filter, cv) => {
        const ctx = cv.getContext("2d");
        const gradient = ctx.createRadialGradient(
            cv.width / 2,
            cv.height / 2,
            0,
            cv.width / 2,
            cv.height / 2,
            Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0.2, "#D0BA8E");
        gradient.addColorStop(1, "#1D0210");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "overlay", 0.2],
            ["sepia", 0.2],
            ["contrast", -0.1],
        ]);
    },

    inkwell: (filter, cv) => {
        applyAll(filter, [
            ["sepia", 0.3],
            ["brightness", 0.1],
            ["contrast", -0.1],
            ["desaturateLuminance"],
        ]);
    },

    // Needs hue blending mode for perfect reproduction. Close enough?
    maven: (filter, cv) => {
        applyAll(filter, [
            ["sepia", 0.25],
            ["brightness", -0.05],
            ["contrast", -0.05],
            ["saturation", 0.5],
        ]);
    },

    toaster: (filter, cv) => {
        const ctx = cv.getContext("2d");
        const gradient = ctx.createRadialGradient(
            cv.width / 2,
            cv.height / 2,
            0,
            cv.width / 2,
            cv.height / 2,
            Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0, "#0F4E80");
        gradient.addColorStop(1, "#3B003B");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "screen", 0.5],
            ["brightness", -0.1],
            ["contrast", 0.5],
        ]);
    },

    walden: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "#CC4400";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "screen", 0.3],
            ["sepia", 0.3],
            ["brightness", 0.1],
            ["saturation", 0.6],
            ["hue", 350],
        ]);
    },

    valencia: (filter, cv) => {
        const ctx = cv.getContext("2d");
        ctx.fillStyle = "#3A0339";
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "exclusion", 0.5],
            ["sepia", 0.08],
            ["brightness", 0.08],
            ["contrast", 0.08],
        ]);
    },

    xpro: (filter, cv) => {
        const ctx = cv.getContext("2d");
        const gradient = ctx.createRadialGradient(
            cv.width / 2,
            cv.height / 2,
            0,
            cv.width / 2,
            cv.height / 2,
            Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0.4, "#E0E7E6");
        gradient.addColorStop(1, "#2B2AA1");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ["blend", cv, "color-burn", 0.7],
            ["sepia", 0.3],
        ]);
    },

    custom: (filter, cv, filterOptions) => {
        const options = Object.assign(
            {
                blend: "normal",
                filterColor: "",
                blur: "0",
                desaturateLuminance: "0",
                saturation: "0",
                contrast: "0",
                brightness: "0",
                sepia: "0",
            },
            JSON.parse(filterOptions || "{}")
        );
        const filters = [];
        if (options.filterColor) {
            const ctx = cv.getContext("2d");
            ctx.fillStyle = options.filterColor;
            ctx.fillRect(0, 0, cv.width, cv.height);
            filters.push(["blend", cv, options.blend, 1]);
        }
        delete options.blend;
        delete options.filterColor;
        filters.push(
            ...Object.entries(options).map(([filter, amount]) => [filter, parseInt(amount) / 100])
        );
        applyAll(filter, filters);
    },
};

/**
 * Applies data-attributes modifications to an img tag and returns a dataURL
 * containing the result. This function does not modify the original image.
 *
 * @param {HTMLImageElement} img the image to which modifications are applied
 * @param {Cropper} cropper the cropper instance
 * @returns {string} dataURL of the image with the applied modifications
 */
export async function applyModifications(img, cropper, dataOptions = {}) {
    const data = Object.assign(
        {
            glFilter: "",
            filter: "#0000",
            quality: "75",
            forceModification: false,
        },
        img.dataset,
        dataOptions
    );
    let {
        width,
        height,
        resizeWidth,
        quality,
        filter,
        mimetype,
        originalSrc,
        glFilter,
        filterOptions,
        forceModification,
        perspective,
        svgAspectRatio,
        imgAspectRatio,
    } = data;
    [width, height, resizeWidth] = [width, height, resizeWidth].map((s) => parseFloat(s));
    quality = parseInt(quality);

    // Skip modifications (required to add shapes on animated GIFs).
    if (isGif(mimetype) && !forceModification) {
        return await _loadImageDataURL(originalSrc);
    }

    // Crop
    const container = document.createElement("div");
    const original = await loadImage(originalSrc);
    // loadImage may have ended up loading a different src (see: LOAD_IMAGE_404)
    originalSrc = original.getAttribute("src");
    container.appendChild(original);
    let croppedImg = cropper.getCroppedCanvas(width, height);

    // Aspect Ratio
    if (imgAspectRatio) {
        document.createElement("div").appendChild(croppedImg);
        imgAspectRatio = imgAspectRatio.split(":");
        imgAspectRatio = parseFloat(imgAspectRatio[0]) / parseFloat(imgAspectRatio[1]);
        const croppedCropper = await activateCropper(croppedImg, imgAspectRatio, { y: 0 });
        croppedImg = croppedCropper.cropper("getCroppedCanvas");
        croppedCropper.destroy();
    }

    // Width
    const result = document.createElement("canvas");
    result.width = resizeWidth || croppedImg.width;
    result.height = perspective
        ? result.width / svgAspectRatio
        : (croppedImg.height * result.width) / croppedImg.width;
    const ctx = result.getContext("2d");
    ctx.imageSmoothingQuality = "high";
    ctx.mozImageSmoothingEnabled = true;
    ctx.webkitImageSmoothingEnabled = true;
    ctx.msImageSmoothingEnabled = true;
    ctx.imageSmoothingEnabled = true;

    // Perspective 3D
    if (perspective) {
        // x, y coordinates of the corners of the image as a percentage
        // (relative to the width or height of the image) needed to apply
        // the 3D effect.
        const points = JSON.parse(perspective);
        const divisions = 10;
        const w = croppedImg.width,
            h = croppedImg.height;

        const project = getProjective(w, h, [
            [(result.width / 100) * points[0][0], (result.height / 100) * points[0][1]], // Top-left [x, y]
            [(result.width / 100) * points[1][0], (result.height / 100) * points[1][1]], // Top-right [x, y]
            [(result.width / 100) * points[2][0], (result.height / 100) * points[2][1]], // bottom-right [x, y]
            [(result.width / 100) * points[3][0], (result.height / 100) * points[3][1]], // bottom-left [x, y]
        ]);

        for (let i = 0; i < divisions; i++) {
            for (let j = 0; j < divisions; j++) {
                const [dx, dy] = [w / divisions, h / divisions];

                const upper = {
                    origin: [i * dx, j * dy],
                    sides: [dx, dy],
                    flange: 0.1,
                    overlap: 0,
                };
                const lower = {
                    origin: [i * dx + dx, j * dy + dy],
                    sides: [-dx, -dy],
                    flange: 0,
                    overlap: 0.1,
                };

                for (let { origin, sides, flange, overlap } of [upper, lower]) {
                    const [[a, c, e], [b, d, f]] = getAffineApproximation(project, [
                        origin,
                        [origin[0] + sides[0], origin[1]],
                        [origin[0], origin[1] + sides[1]],
                    ]);

                    const ox = (i !== divisions ? overlap * sides[0] : 0) + flange * sides[0];
                    const oy = (j !== divisions ? overlap * sides[1] : 0) + flange * sides[1];

                    origin[0] += flange * sides[0];
                    origin[1] += flange * sides[1];

                    sides[0] -= flange * sides[0];
                    sides[1] -= flange * sides[1];

                    ctx.save();
                    ctx.setTransform(a, b, c, d, e, f);

                    ctx.beginPath();
                    ctx.moveTo(origin[0] - ox, origin[1] - oy);
                    ctx.lineTo(origin[0] + sides[0], origin[1] - oy);
                    ctx.lineTo(origin[0] + sides[0], origin[1]);
                    ctx.lineTo(origin[0], origin[1] + sides[1]);
                    ctx.lineTo(origin[0] - ox, origin[1] + sides[1]);
                    ctx.closePath();
                    ctx.clip();
                    ctx.drawImage(croppedImg, 0, 0);

                    ctx.restore();
                }
            }
        }
    } else {
        ctx.drawImage(
            croppedImg,
            0,
            0,
            croppedImg.width,
            croppedImg.height,
            0,
            0,
            result.width,
            result.height
        );
    }

    // GL filter
    if (glFilter) {
        const glf = new window.WebGLImageFilter();
        const cv = document.createElement("canvas");
        cv.width = result.width;
        cv.height = result.height;
        applyAll = _applyAll.bind(null, result);
        glFilters[glFilter](glf, cv, filterOptions);
        const filtered = glf.apply(result);
        ctx.drawImage(
            filtered,
            0,
            0,
            filtered.width,
            filtered.height,
            0,
            0,
            result.width,
            result.height
        );
    }

    // Color filter
    ctx.fillStyle = filter || "#0000";
    ctx.fillRect(0, 0, result.width, result.height);

    // Quality
    const dataURL = result.toDataURL(mimetype, quality / 100);
    const newSize = getDataURLBinarySize(dataURL);
    const originalSize = _getImageSizeFromCache(originalSrc);
    const isChanged =
        !!perspective ||
        !!glFilter ||
        original.width !== result.width ||
        original.height !== result.height ||
        original.width !== croppedImg.width ||
        original.height !== croppedImg.height;
    return isChanged || originalSize >= newSize ? dataURL : await _loadImageDataURL(originalSrc);
}

/**
 * Loads an src into an HTMLImageElement.
 *
 * @param {String} src URL of the image to load
 * @param {HTMLImageElement} [img] img element in which to load the image
 * @returns {Promise<HTMLImageElement>} Promise that resolves to the loaded img
 *     or a placeholder image if the src is not found.
 */
export function loadImage(src, img = new Image()) {
    const handleImage = (source, resolve, reject) => {
        img.addEventListener("load", () => resolve(img), { once: true });
        img.addEventListener("error", reject, { once: true });
        img.src = source;
    };
    // The server will return a placeholder image with the following src.
    // grep: LOAD_IMAGE_404
    const placeholderHref = "/web/image/__odoo__unknown__src__/";

    return new Promise((resolve, reject) => {
        fetch(src)
            .then((response) => {
                if (!response.ok) {
                    src = placeholderHref;
                }
                handleImage(src, resolve, reject);
            })
            .catch((error) => {
                src = placeholderHref;
                handleImage(src, resolve, reject);
            });
    });
}

// Because cropperjs acquires images through XHRs on the image src and we don't
// want to load big images over the network many times when adjusting quality
// and filter, we create a local cache of the images using object URLs.
const imageCache = new Map();

/**
 * Loads image object URL into cache if not already set and returns it.
 *
 * @param {String} src
 * @returns {Promise}
 */
function _loadImageObjectURL(src) {
    return _updateImageData(src);
}

/**
 * Gets image dataURL from cache in the same way as object URL.
 *
 * @param {String} src
 * @returns {Promise}
 */
function _loadImageDataURL(src) {
    return _updateImageData(src, "dataURL");
}

/**
 * @param {String} src used as a key on the image cache map.
 * @param {String} [key='objectURL'] specifies the image data to update/return.
 * @returns {Promise<String>} resolves with either dataURL/objectURL value.
 */
async function _updateImageData(src, key = "objectURL") {
    const currentImageData = imageCache.get(src);
    if (currentImageData && currentImageData[key]) {
        return currentImageData[key];
    }
    let value = "";
    const blob = await fetch(src).then((res) => res.blob());
    if (key === "dataURL") {
        value = await createDataURL(blob);
    } else {
        value = URL.createObjectURL(blob);
    }
    imageCache.set(src, Object.assign(currentImageData || {}, { [key]: value, size: blob.size }));
    return value;
}

/**
 * Returns the size of a cached image.
 * Warning: this supposes that the image is already in the cache, i.e. that
 * _updateImageData was called before.
 *
 * @param {String} src used as a key on the image cache map.
 * @returns {Number} size of the image in bytes.
 */
function _getImageSizeFromCache(src) {
    return imageCache.get(src).size;
}

/**
 * Activates the cropper on a given image.
 *
 * @param {jQuery} $image the image on which to activate the cropper
 * @param {Number} aspectRatio the aspectRatio of the crop box
 * @param {DOMStringMap} dataset dataset containing the cropperDataFields
 */
export async function activateCropper(image, aspectRatio, dataset) {
    const oldSrc = image.src;
    const newSrc = await _loadImageObjectURL(image.getAttribute("src"));
    image.src = newSrc;
    // eslint-disable-next-line no-undef
    const cropper = new Cropper(image, {
        viewMode: 2,
        dragMode: "move",
        autoCropArea: 1.0,
        aspectRatio: aspectRatio,
        data: Object.fromEntries(
            Object.entries(pick(dataset, ...cropperDataFields)).map(([key, value]) => [
                key,
                parseFloat(value),
            ])
        ),
        // Can't use 0 because it's falsy and cropperjs will then use its defaults (200x100)
        minContainerWidth: 1,
        minContainerHeight: 1,
    });
    if (oldSrc === newSrc && image.complete) {
        return;
    }
    return cropper;
}

/**
 * Marks an <img> with its attachment data (originalId, originalSrc, mimetype)
 *
 * @param {HTMLImageElement} img the image whose attachment data should be found
 * @param {string} [attachmentSrc=''] specifies the URL of the corresponding
 * attachment if it can't be found in the 'src' attribute.
 */
export async function loadImageInfo(img, attachmentSrc = "") {
    const src = attachmentSrc || img.getAttribute("src");
    // If there is a marked originalSrc, the data is already loaded.
    // If the image does not have the "mimetypeBeforeConversion" attribute, it
    // has to be added.
    if ((img.dataset.originalSrc && img.dataset.mimetypeBeforeConversion) || !src) {
        return;
    }
    // In order to be robust to absolute, relative and protocol relative URLs,
    // the src of the img is first converted to an URL object. To do so, the URL
    // of the document in which the img is located is used as a base to build
    // the URL object if the src of the img is a relative or protocol relative
    // URL. The original attachment linked to the img is then retrieved thanks
    // to the path of the built URL object.
    let docHref = img.ownerDocument.defaultView.location.href;
    if (docHref.startsWith("about:")) {
        docHref = window.location.href;
    }

    const srcUrl = new URL(src, docHref);
    const relativeSrc = srcUrl.pathname;

    const { original } = await rpc("/html_editor/get_image_info", { src: relativeSrc });
    // If src was an absolute "external" URL, we consider unlikely that its
    // relative part matches something from the DB and even if it does, nothing
    // bad happens, besides using this random image as the original when using
    // the options, instead of having no option. Note that we do not want to
    // check if the image is local or not here as a previous bug converted some
    // local (relative src) images to absolute URL... and that before users had
    // setup their website domain. That means they can have an absolute URL that
    // looks like "https://mycompany.odoo.com/web/image/123" that leads to a
    // "local" image even if the domain name is now "mycompany.be".
    //
    // The "redirect" check is for when it is a redirect image attachment due to
    // an external URL upload.
    if (
        original &&
        original.image_src &&
        !/\/web\/image\/\d+-redirect\//.test(original.image_src)
    ) {
        if (!img.dataset.mimetype) {
            // The mimetype has to be added only if it is not already present as
            // we want to avoid to reset a mimetype set by the user.
            img.dataset.mimetype = original.mimetype;
        }
        img.dataset.originalId = original.id;
        img.dataset.originalSrc = original.image_src;
        img.dataset.mimetypeBeforeConversion = original.mimetype;
    }
}

/**
 * @param {Blob} blob
 * @returns {Promise}
 */
export function createDataURL(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.addEventListener("load", () => resolve(reader.result));
        reader.addEventListener("abort", reject);
        reader.addEventListener("error", reject);
        reader.readAsDataURL(blob);
    });
}

/**
 * @param {String} dataURL
 * @returns {Number} number of bytes represented with base64
 */
export function getDataURLBinarySize(dataURL) {
    // Every 4 bytes of base64 represent 3 bytes.
    return (dataURL.split(",")[1].length / 4) * 3;
}
