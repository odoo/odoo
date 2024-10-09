/**
 * @private
 * @param {HTMLImageElement} img
 * @returns {String} The right mimetype used to apply options on image.
 */
export function getImageMimetype(img) {
    if (img.dataset.shape && img.dataset.originalMimetype) {
        return img.dataset.originalMimetype;
    }
    return img.dataset.mimetype;
}

export function getShapeURL(shapeName) {
    const [module, directory, fileName] = shapeName.split("/");
    return `/${encodeURIComponent(module)}/static/image_shapes/${encodeURIComponent(
        directory
    )}/${encodeURIComponent(fileName)}.svg`;
}
