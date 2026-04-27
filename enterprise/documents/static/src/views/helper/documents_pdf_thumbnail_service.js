/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { Mutex } from "@web/core/utils/concurrency";
import { loadPDFJSAssets } from "@web/libs/pdfjs";
import { useComponent } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

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
                record.data.thumbnail_status !== "client_generated" ||
                record.hasStoredThumbnail() ||
                !enabled
            ) {
                return;
            }
            try {
                await loadPDFJSAssets();
                // Force usage of worker to avoid hanging the tab.
                initialWorkerSrc = globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc;
                globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc =
                    "/web/static/lib/pdfjs/build/pdf.worker.js";
            } catch {
                enabled = false;
                return;
            }
            let thumbnail = undefined;
            try {
                const pdf = await globalThis.pdfjsLib.getDocument(
                    `/documents/content/${encodeURIComponent(record.data.access_token)}?download=0`
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

                thumbnail = canvas.toDataURL("image/jpeg").replace("data:image/jpeg;base64,", "");
            } catch (_error) {
                if (
                    _error.name !== "UnexpectedResponseException" &&
                    _error.status &&
                    _error.status !== 403
                ) {
                    thumbnail = false;
                }
            } finally {
                if (thumbnail !== undefined) {
                    await rpc(`/documents/document/${record.resId}/update_thumbnail`, {
                        thumbnail,
                    });
                    record.data.thumbnail_status = thumbnail ? "present" : "error";
                    if (thumbnail) {
                        env.bus.trigger("documents-new-pdf-thumbnail", { record });
                    }
                }
                // Restore pdfjs's state
                globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
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
