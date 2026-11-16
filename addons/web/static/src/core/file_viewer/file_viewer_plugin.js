import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";
import { FileViewer } from "./file_viewer";

/**
 * @import { File } from "@web/core/file_viewer/file_viewer";
 */

export class FileViewerPlugin extends Plugin {
    #overlay = usePlugin(OverlayPlugin);

    /**
     * @param {import("@odoo/owl").Signal<HTMLElement | null>} [ref]
     */
    createFileViewer(ref) {
        const overlay = this.#overlay;
        let closeFn = () => {};

        function close() {
            closeFn();
        }

        /**
         * @param {File} file the file to open in the viewer
         * @param {File[]} files
         * @param {Object} [options]
         * @param {(f: File) => boolean} [options.canUnlink]
         * @param {(f: File) => boolean} [options.onUnlink] called when the user requests to unlink the file. * Returns `true` on success, allowing the file viewer to close.
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

        return { open, close };
    }
}

services.add(FileViewerPlugin);

/**
 * @param {import("@odoo/owl").Signal<HTMLElement | null>} [ref]
 */
export function useFileViewer(ref) {
    const fileViewer = usePlugin(FileViewerPlugin).createFileViewer(ref);
    onWillDestroy(fileViewer.close);
    return fileViewer;
}
