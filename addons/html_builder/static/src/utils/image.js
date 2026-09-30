import { loadImageInfo } from "@html_editor/utils/image_processing";
import { getFetchedMimetype } from "@html_editor/utils/image";

export async function getMimetypeBeforeShape(imageEl) {
    const data = imageEl.dataset;
    const { formatMimetype, mimetypeBeforeConversion } = data.mimetypeBeforeConversion
        ? data
        : await loadImageInfo(imageEl);
    return formatMimetype || mimetypeBeforeConversion || getFetchedMimetype(imageEl, data);
}

/**
 * Executes a callback for each <img> element in a collection if the given node
 * contains a specific data-* attribute.
 * @param {Array<HTMLElement>} toProcessEls
 * @param {HTMLElement} nodeEl
 * @param {String} dataInfo
 * @param {Function} callback
 */
export async function handleImagesIfDataset(toProcessEls, nodeEl, dataInfo, callback) {
    if (!nodeEl || !nodeEl.dataset[dataInfo]) {
        return;
    }
    for (const toProcessEl of toProcessEls) {
        if (!toProcessEl || !toProcessEl.tagName === "IMG") {
            continue;
        }
        await callback(toProcessEl, nodeEl);
    }
}
