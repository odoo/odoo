/* @odoo-module */

import { onWillDestroy } from "@odoo/owl";
import { FileViewer } from "./file_viewer";
import { useService } from "../utils/hooks";

export function useFileViewer() {
    const overlay = useService("overlay");
    let removeFileViewer = null;

    /**
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files[]} file
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files} files
     */
    function open(file, files = [file]) {
        if (!file.isViewable) {
            return;
        }
        if (files.length > 0) {
            const viewableFiles = files.filter((file) => file.isViewable);
            const index = viewableFiles.indexOf(file);
            removeFileViewer = overlay.add(FileViewer, {
                files: viewableFiles,
                startIndex: index,
                close,
            });
        }
    }

    function close() {
        removeFileViewer?.();
    }
    onWillDestroy(close);
    return { open, close };
}
