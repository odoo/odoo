odoo.define('web_editor.image_processing', function (require) {
'use strict';

// Fields returned by cropperjs 'getData' method, also need to be passed when
// initializing the cropper to reuse the previous crop.
const cropperDataFields = ['x', 'y', 'width', 'height', 'rotate', 'scaleX', 'scaleY'];
const modifierFields = [
    'filter',
    'quality',
    'mimetype',
    'glFilter',
    'originalId',
    'originalSrc',
    'resizeWidth',
    'aspectRatio',
];

// webgl color filters
const _applyAll = (result, filter, filters) => {
    filters.forEach(f => {
        if (f[0] === 'blend') {
            const cv = f[1];
            const ctx = result.getContext('2d');
            ctx.globalCompositeOperation = f[2];
            ctx.globalAlpha = f[3];
            ctx.drawImage(cv, 0, 0);
            ctx.globalCompositeOperation = 'source-over';
            ctx.globalAlpha = 1.0;
        } else {
            filter.addFilter(...f);
        }
    });
};
let applyAll;

const glFilters = {
    blur: filter => filter.addFilter('blur', 10),

    '1977': (filter, cv) => {
        const ctx = cv.getContext('2d');
        ctx.fillStyle = 'rgb(243, 106, 188)';
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'screen', .3],
            ['brightness', .1],
            ['contrast', .1],
            ['saturation', .3],
        ]);
    },

    aden: (filter, cv) => {
        const ctx = cv.getContext('2d');
        ctx.fillStyle = 'rgb(66, 10, 14)';
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'darken', .2],
            ['brightness', .2],
            ['contrast', -.1],
            ['saturation', -.15],
            ['hue', 20],
        ]);
    },

    brannan: (filter, cv) => {
        const ctx = cv.getContext('2d');
        ctx.fillStyle = 'rgb(161, 44, 191)';
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'lighten', .31],
            ['sepia', .5],
            ['contrast', .4],
        ]);
    },

    earlybird: (filter, cv) => {
        const ctx = cv.getContext('2d');
        const gradient = ctx.createRadialGradient(
            cv.width / 2, cv.height / 2, 0,
            cv.width / 2, cv.height / 2, Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(.2, '#D0BA8E');
        gradient.addColorStop(1, '#1D0210');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'overlay', .2],
            ['sepia', .2],
            ['contrast', -.1],
        ]);
    },

    inkwell: (filter, cv) => {
        applyAll(filter, [
            ['sepia', .3],
            ['brightness', .1],
            ['contrast', -.1],
            ['desaturateLuminance'],
        ]);
    },

    // Needs hue blending mode for perfect reproduction. Close enough?
    maven: (filter, cv) => {
        applyAll(filter, [
            ['sepia', .25],
            ['brightness', -.05],
            ['contrast', -.05],
            ['saturation', .5],
        ]);
    },

    toaster: (filter, cv) => {
        const ctx = cv.getContext('2d');
        const gradient = ctx.createRadialGradient(
            cv.width / 2, cv.height / 2, 0,
            cv.width / 2, cv.height / 2, Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(0, '#0F4E80');
        gradient.addColorStop(1, '#3B003B');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'screen', .5],
            ['brightness', -.1],
            ['contrast', .5],
        ]);
    },

    walden: (filter, cv) => {
        const ctx = cv.getContext('2d');
        ctx.fillStyle = '#CC4400';
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'screen', .3],
            ['sepia', .3],
            ['brightness', .1],
            ['saturation', .6],
            ['hue', 350],
        ]);
    },

    valencia: (filter, cv) => {
        const ctx = cv.getContext('2d');
        ctx.fillStyle = '#3A0339';
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'exclusion', .5],
            ['sepia', .08],
            ['brightness', .08],
            ['contrast', .08],
        ]);
    },

    xpro: (filter, cv) => {
        const ctx = cv.getContext('2d');
        const gradient = ctx.createRadialGradient(
            cv.width / 2, cv.height / 2, 0,
            cv.width / 2, cv.height / 2, Math.hypot(cv.width, cv.height) / 2
        );
        gradient.addColorStop(.4, '#E0E7E6');
        gradient.addColorStop(1, '#2B2AA1');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, cv.width, cv.height);
        applyAll(filter, [
            ['blend', cv, 'color-burn', .7],
            ['sepia', .3],
        ]);
    },

    custom: (filter, cv, filterOptions) => {
        const options = Object.assign({
            blend: 'normal',
            filterColor: '',
            blur: '0',
            desaturateLuminance: '0',
            saturation: '0',
            contrast: '0',
            brightness: '0',
            sepia: '0',
        }, JSON.parse(filterOptions || "{}"));
        const filters = [];
        if (options.filterColor) {
            const ctx = cv.getContext('2d');
            ctx.fillStyle = options.filterColor;
            ctx.fillRect(0, 0, cv.width, cv.height);
            filters.push(['blend', cv, options.blend, 1]);
        }
        delete options.blend;
        delete options.filterColor;
        filters.push(...Object.entries(options).map(([filter, amount]) => [filter, parseInt(amount) / 100]));
        applyAll(filter, filters);
    },
};
/**
 * Applies data-attributes modifications to an img tag and returns a dataURL
 * containing the result. This function does not modify the original image.
 *
 * @param {HTMLImageElement} img the image to which modifications are applied
 * @returns {string} dataURL of the image with the applied modifications
 */
async function applyModifications(img) {
    const data = Object.assign({
        glFilter: '',
        filter: '#0000',
        quality: '75',
    }, img.dataset);
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
    } = data;
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

    // GL filter
    if (glFilter) {
        const glf = new window.WebGLImageFilter();
        const cv = document.createElement('canvas');
        cv.width = result.width;
        cv.height = result.height;
        applyAll = _applyAll.bind(null, result);
        glFilters[glFilter](glf, cv, filterOptions);
        const filtered = glf.apply(result);
        ctx.drawImage(filtered, 0, 0, filtered.width, filtered.height, 0, 0, result.width, result.height);
    }

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
    const src = img.getAttribute('src');
    // If there is a marked originalSrc, the data is already loaded.
    if (img.dataset.originalSrc || !src) {
        return;
    }

    const {original} = await rpc({
        route: '/web_editor/get_image_info',
        params: {src: src.split(/[?#]/)[0]},
    });
    // Check that url is local.
    const isLocal = original && new URL(original.image_src, window.location.origin).origin === window.location.origin;
    if (isLocal && original.image_src) {
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
