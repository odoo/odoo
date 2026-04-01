import { onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FileViewer } from "./file_viewer";

let id = 1;

export function createFileViewer() {
    const fileViewerId = `web.file_viewer${id++}`;
    /**
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files[]} file
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files} files
     */
    function open(file, files = [file]) {
        close();
        if (!file.isViewable) {
            return;
        }
        if (files.length > 0) {
            const viewableFiles = files.filter((file) => file.isViewable);
            const index = viewableFiles.indexOf(file);
            registry.category("main_components").add(fileViewerId, {
                Component: FileViewer,
                props: { files: viewableFiles, startIndex: index, close },
            });
        }
    }

    function close() {
        registry.category("main_components").remove(fileViewerId);
    }
    return { open, close };
}

export function useFileViewer() {
    const { open, close } = createFileViewer();
    onWillDestroy(close);
    return { open, close };
}
