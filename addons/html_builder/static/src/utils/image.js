import { loadImageInfo } from "@html_editor/utils/image_processing";
import { getMimetype } from "@html_editor/utils/image";

export async function getMimetypeBeforeShape(imageEl) {
    const data = imageEl.dataset;
    const { formatMimetype, mimetypeBeforeConversion } = data.mimetypeBeforeConversion
        ? data
        : await loadImageInfo(imageEl);
    return formatMimetype || mimetypeBeforeConversion || getMimetype(imageEl, data);
}
