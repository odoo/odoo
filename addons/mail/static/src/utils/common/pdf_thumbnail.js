import { loadPDFJSAssets } from "@web/core/utils/pdfjs";

export async function generatePdfThumbnail(
    pdfUrl,
    options = { width: 180, height: 110, stripBase64Prefix: false }
) {
    let initialWorkerSrc = false;
    try {
        await loadPDFJSAssets();
        // Force usage of worker to avoid hanging the tab.
        initialWorkerSrc = globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc;
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc =
            "/web/static/lib/pdfjs/build/pdf.worker.js";
    } catch {
        return { thumbnail: undefined, pdfEnabled: false };
    }
    let canvas, thumbnail;
    try {
        let pdf;
        // Support for blob url
        if (pdfUrl.startsWith("blob:")) {
            pdfUrl = URL.createObjectURL(pdfUrl);
            pdf = await globalThis.pdfjsLib.getDocument(pdfUrl).promise;
            URL.revokeObjectURL(pdfUrl);
        } else {
            pdf = await globalThis.pdfjsLib.getDocument(pdfUrl).promise;
        }
        const page = await pdf.getPage(1);
        // Render first page onto a canvas
        const viewPort = page.getViewport({ scale: 1 });
        canvas = document.createElement("canvas");
        canvas.width = options.width;
        canvas.height = options.height;
        const scale = canvas.width / viewPort.width;
        await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport: page.getViewport({ scale }),
        }).promise;
    } catch (_error) {
        if (
            _error.name !== "UnexpectedResponseException" &&
            _error.status &&
            _error.status !== 403
        ) {
            canvas = undefined;
        }
    } finally {
        // Restore pdfjs's state
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
        if (canvas) {
            thumbnail = canvas.toDataURL("image/jpeg");
            if (options.stripBase64Prefix) {
                thumbnail = thumbnail.replace("data:image/jpeg;base64,", "");
            }
        }
    }
    return { thumbnail, pdfEnabled: true };
}
