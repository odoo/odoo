import { rpc } from "@web/core/network/rpc";
import { pick } from "@web/core/utils/objects";
import { loadBundle } from "@web/core/assets";

// Fields returned by cropperjs 'getData' method, also need to be passed when
// initializing the cropper to reuse the previous crop.
export const cropperDataFields = ["x", "y", "width", "height", "rotate", "scaleX", "scaleY"];
export const cropperDataFieldsWithAspectRatio = [...cropperDataFields, "aspectRatio"];
export const isGif = (mimetype) => mimetype === "image/gif";
const modifierFields = [
    "filter",
    "quality",
    "mimetype",
    "glFilter",
    "originalId",
    "originalSrc",
    "resizeWidth",
    "aspectRatio",
    "bgSrc",
    "mimetypeBeforeConversion",
];

export const removeOnImageChangeAttrs = [...cropperDataFields, ...modifierFields];

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
export function loadImageDataURL(src) {
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
export function getImageSizeFromCache(src) {
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
    await loadBundle("html_editor.assets_image_cropper");
    const oldSrc = image.src;
    const newSrc = await _loadImageObjectURL(image.getAttribute("src"));
    image.src = newSrc;
    let readyResolve;
    const readyPromise = new Promise((resolve) => (readyResolve = resolve));
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
        ready: readyResolve,
    });
    if (oldSrc === newSrc && image.complete) {
        return;
    }
    await readyPromise;
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
    const newDataset = {};
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
            newDataset.mimetype = original.mimetype;
        }
        newDataset.originalId = original.id;
        newDataset.originalSrc = original.image_src;
        newDataset.mimetypeBeforeConversion = original.mimetype;
    }
    return newDataset;
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

/**
 * Returns the aspect ratio from a string or number.
 * If the input is a string, it can be a ratio (e.g. "16:9") or a single number.
 * If the input is a number, it is returned as is.
 *
 * @param {string|number} ratio
 * @returns {number}
 */
export function getAspectRatio(ratio) {
    if (typeof ratio === "number") {
        return ratio;
    }
    const [a, b] = ratio.split(/[:/]/).map((n) => parseFloat(n));
    // If the ratio is invalid, return only a.
    if (!b) {
        return a;
    }
    return a / b;
}
