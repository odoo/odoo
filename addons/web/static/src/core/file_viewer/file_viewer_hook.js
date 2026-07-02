import { onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "../utils/hooks";
import { FileViewer } from "./file_viewer";

const fileViewerService = {
    dependencies: ["overlay"],
    start(_env, { overlay }) {
        return function createFileViewer() {
            let closeFn;
            /**
             * @param {import("@web/core/file_viewer/file_viewer").File} file
             * @param {import("@web/core/file_viewer/file_viewer").File[]} files
             */
            function open(file, files = [file]) {
                closeFn?.();
                if (!file.isViewable) {
                    return;
                }
                if (files.length > 0) {
                    const viewableFiles = files.filter((file) => file.isViewable);
                    const index = viewableFiles.indexOf(file);
                    closeFn = overlay.add(FileViewer, {
                        files: viewableFiles,
                        startIndex: index,
                        close: () => closeFn?.(),
                    });
                }
            }
            return { open, close: () => closeFn?.() };
        };
    },
};
registry.category("services").add("fileViewer", fileViewerService);

export function useFileViewer() {
    const createFileViewer = useService("fileViewer");
    const { open, close } = createFileViewer();
    onWillDestroy(close);
    return { open, close };
}
