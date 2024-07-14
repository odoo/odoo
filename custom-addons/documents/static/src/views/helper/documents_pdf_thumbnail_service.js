/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { Mutex } from "@web/core/utils/concurrency";
import { loadBundle } from "@web/core/assets";
import { useComponent } from "@odoo/owl";

export const documentsPdfThumbnailService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let enabled = true;
        const mutex = new Mutex();

        const width = 200;
        const height = 140;

        let queue = Promise.resolve();

        const checkForThumbnail = async (record) => {
            let initialWorkerSrc = false;
            if (
                !record.isPdf() ||
                record.hasThumbnail() ||
                record.data.thumbnail_status === "error" ||
                !enabled
            ) {
                return;
            }
            try {
                try {
                    await loadBundle("documents.pdf_js_assets");
                } catch {
                    await loadBundle("web.pdf_js_lib");
                }
                // Force usage of worker to avoid hanging the tab.
                initialWorkerSrc = window.pdfjsLib.GlobalWorkerOptions.workerSrc;
                window.pdfjsLib.GlobalWorkerOptions.workerSrc =
                    "web/static/lib/pdfjs/build/pdf.worker.js";
            } catch {
                enabled = false;
                return;
            }
            const writeData = {};
            try {
                const pdf = await window.pdfjsLib.getDocument(
                    `/documents/pdf_content/${record.resId}`
                ).promise;
                const page = await pdf.getPage(1);

                // Render first page onto a canvas
                const viewPort = page.getViewport({ scale: 1 });
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const scale = canvas.width / viewPort.width;
                await page.render({
                    canvasContext: canvas.getContext("2d"),
                    viewport: page.getViewport({ scale }),
                }).promise;

                writeData.thumbnail = canvas
                    .toDataURL("image/jpeg")
                    .replace("data:image/jpeg;base64,", "");
                writeData.thumbnail_status = "present";
            } catch (_error) {
                if (
                    _error.name !== "UnexpectedResponseException" &&
                    _error.status &&
                    _error.status !== 403
                ) {
                    writeData.thumbnail_status = "error";
                }
            } finally {
                if (Object.keys(writeData).length) {
                    await orm.write("documents.document", [record.resId], writeData);
                    record.data.thumbnail_status = writeData.thumbnail_status;
                    if (writeData.thumbnail) {
                        env.bus.trigger("documents-new-pdf-thumbnail", { record });
                    }
                }
                // Restore pdfjs's state
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
            }
        };
        const enqueueRecord = (record) => {
            queue = queue.then(() => checkForThumbnail(record));
        };

        return {
            enqueueRecords(records) {
                if (!enabled || env.isSmall) {
                    return;
                }
                mutex.exec(() => {
                    for (const record of records) {
                        enqueueRecord(record);
                    }
                });
            },
        };
    },
};

export function onNewPdfThumbnail(callback) {
    const component = useComponent();
    useBus(component.env.bus, "documents-new-pdf-thumbnail", callback);
}

registry.category("services").add("documents_pdf_thumbnail", documentsPdfThumbnailService);
