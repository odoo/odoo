odoo.define('web_editor.image_processing', function (require) {
'use strict';

// Fields returned by cropperjs 'getData' method, also need to be passed when
// initializing the cropper to reuse the previous crop.
const cropperDataFields = ['x', 'y', 'width', 'height', 'rotate', 'scaleX', 'scaleY'];
const modifierFields = [
    'filter',
    'quality',
    'mimetype',
    'originalId',
    'originalSrc',
    'resizeWidth',
    'aspectRatio',
];
/**
 * Applies data-attributes modifications to an img tag and returns a dataURL
 * containing the result. This function does not modify the original image.
 *
 * @param {HTMLImageElement} img the image to which modifications are applied
 * @returns {string} dataURL of the image with the applied modifications
 */
async function applyModifications(img) {
    const data = Object.assign({
        filter: '#0000',
        quality: '95',
    }, img.dataset);
    let {width, height, resizeWidth, quality, filter, mimetype, originalSrc} = data;
    [width, height, resizeWidth] = [width, height, resizeWidth].map(s => parseFloat(s));
    quality = parseInt(quality);

    // Crop
    const container = document.createElement('div');
    const original = await loadImage(originalSrc);
    container.appendChild(original);
    await activateCropper(original, 0, data);
    const croppedImg = $(original).cropper('getCroppedCanvas', {width, height});
    $(original).cropper('destroy');

    // Width
    const result = document.createElement('canvas');
    result.width = resizeWidth || croppedImg.width;
    result.height = croppedImg.height * result.width / croppedImg.width;
    const ctx = result.getContext('2d');
    ctx.drawImage(croppedImg, 0, 0, croppedImg.width, croppedImg.height, 0, 0, result.width, result.height);

    // Color filter
    ctx.fillStyle = filter || '#0000';
    ctx.fillRect(0, 0, result.width, result.height);

    // Quality
    return result.toDataURL(mimetype, quality / 100);
}

/**
 * Loads an src into an HTMLImageElement.
 *
 * @param {String} src URL of the image to load
 * @param {HTMLImageElement} [img] img element in which to load the image
 * @returns {Promise<HTMLImageElement>} Promise that resolves to the loaded img
 */
function loadImage(src, img = new Image()) {
    return new Promise((resolve, reject) => {
        img.addEventListener('load', () => resolve(img), {once: true});
        img.addEventListener('error', reject, {once: true});
        img.src = src;
    });
}

// Because cropperjs acquires images through XHRs on the image src and we don't
// want to load big images over the network many times when adjusting quality
// and filter, we create a local cache of the images using object URLs.
const imageCache = new Map();
/**
 * Activates the cropper on a given image.
 *
 * @param {jQuery} $image the image on which to activate the cropper
 * @param {Number} aspectRatio the aspectRatio of the crop box
 * @param {DOMStringMap} dataset dataset containing the cropperDataFields
 */
async function activateCropper(image, aspectRatio, dataset) {
    const src = image.getAttribute('src');
    if (!imageCache.has(src)) {
        const res = await fetch(src);
        imageCache.set(src, URL.createObjectURL(await res.blob()));
    }
    image.src = imageCache.get(src);
    $(image).cropper({
        viewMode: 2,
        dragMode: 'move',
        autoCropArea: 1.0,
        aspectRatio: aspectRatio,
        data: _.mapObject(_.pick(dataset, ...cropperDataFields), value => parseFloat(value)),
        // Can't use 0 because it's falsy and cropperjs will then use its defaults (200x100)
        minContainerWidth: 1,
        minContainerHeight: 1,
    });
    return new Promise(resolve => image.addEventListener('ready', resolve, {once: true}));
}
/**
 * Marks an <img> with its attachment data (originalId, originalSrc, mimetype)
 *
 * @param {HTMLImageElement} img the image whose attachment data should be found
 * @param {Function} rpc a function that can be used to make the RPC. Typically
 *   this would be passed as 'this._rpc.bind(this)' from widgets.
 */
async function loadImageInfo(img, rpc) {
    // If there is a marked originalSrc, the data is already loaded.
    if (img.dataset.originalSrc) {
        return;
    }

    const {original} = await rpc({
        route: '/web_editor/get_image_info',
        params: {src: img.getAttribute('src').split(/[?#]/)[0]},
    });
    // Check that url is local.
    if (original && new URL(original.image_src, window.location.origin).origin === window.location.origin) {
        img.dataset.originalId = original.id;
        img.dataset.originalSrc = original.image_src;
        img.dataset.mimetype = original.mimetype;
    }
}

return {
    applyModifications,
    cropperDataFields,
    activateCropper,
    loadImageInfo,
    loadImage,
    removeOnImageChangeAttrs: [...cropperDataFields, ...modifierFields, 'aspectRatio'],
};
});
