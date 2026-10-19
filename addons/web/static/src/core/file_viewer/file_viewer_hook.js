import { onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "../utils/hooks";
import { FileViewer } from "./file_viewer";

/** @typedef {import("@web/core/file_viewer/file_viewer").File} File */

const fileViewerService = {
    dependencies: ["overlay"],
    /**
     * @param {import("@web/env").OdooEnv} _env
     * @param {import("services").Services} services
     */
    start(_env, { overlay }) {
        /**
         * @param {import("@odoo/owl").Signal<HTMLElement | null>} [ref]
         */
        function createFileViewer(ref) {
            function close() {
                closeFn();
            }

            /**
             * @param {File} file the file to open in the viewer
             * @param {File[]} files
             * @param {Object} [options]
             * @param {(File) => boolean} [options.canUnlink]
             * @param {(File) => boolean} [options.onUnlink] called when the user requests to unlink the file. * Returns `true` on success, allowing the file viewer to close.
             */
            function open(file, files = [file], { canUnlink, onUnlink } = {}) {
                close();
                if (!file.isViewable) {
                    return;
                }
                if (files.length > 0) {
                    const viewableFiles = files.filter((file) => file.isViewable);
                    const index = viewableFiles.indexOf(file);
                    closeFn = overlay.add(
                        FileViewer,
                        {
                            files: viewableFiles,
                            startIndex: index,
                            canUnlink,
                            onUnlink,
                            close,
                        },
                        { rootId: ref?.()?.getRootNode()?.host?.id }
                    );
                }
            }

            let closeFn = () => {};

            return { open, close };
        }

        return createFileViewer;
    },
};
registry.category("services").add("fileViewer", fileViewerService);

/**
 * @param {import("@odoo/owl").Signal<HTMLElement | null>} [ref]
 */
export function useFileViewer(ref) {
    const createFileViewer = useService("fileViewer");
    const fileViewer = createFileViewer(ref);
    onWillDestroy(fileViewer.close);
    return fileViewer;
}
