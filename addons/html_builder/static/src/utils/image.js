import { loadImageInfo } from "@html_editor/utils/image_processing";
import { getFetchedMimetype } from "@html_editor/utils/image";

export async function getMimetypeBeforeShape(imageEl) {
    const data = imageEl.dataset;
    const { formatMimetype, mimetypeBeforeConversion } = data.mimetypeBeforeConversion
        ? data
        : await loadImageInfo(imageEl);
    return formatMimetype || mimetypeBeforeConversion || getFetchedMimetype(imageEl, data);
}
