import { onWillDestroy } from "@odoo/owl";
import { FileViewer } from "./file_viewer";
import { useService } from "../utils/hooks";
import { useComponent } from "@web/owl2/utils";
import { registry } from "@web/core/registry";

<<<<<<< c368cd4ba868144f43cc9a4fed368c6b49f8f4b6
const fileViewerService = {
    dependencies: ["overlay"],
    start(_env, { overlay }) {
        return (owner) => {
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
                    closeFn = overlay.add(
                        FileViewer,
                        {
                            files: viewableFiles,
                            startIndex: index,
                            close: () => closeFn?.(),
                        },
                        { rootId: owner?.root?.el?.getRootNode()?.host?.id }
                    );
                }
            }
            return { open, close: () => closeFn?.() };
        };
    },
};
registry.category("services").add("fileViewer", fileViewerService);
||||||| ba2d10f169b8c26d04c5b9fdd491673dc0005768
export function createFileViewer(owner) {
    const overlay = useService("overlay");
    let closeFn;
    /**
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files[]} file
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files} files
     */
    function open(file, files = [file]) {
        closeFn?.();
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
                    close: () => closeFn?.(),
                },
                { rootId: owner?.root?.el?.getRootNode()?.host?.id }
            );
        }
    }
    return { open, close: () => closeFn?.() };
}
=======
export function createFileViewer(owner) {
    const overlay = useService("overlay");
    let closeFn;
    /**
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files[]} file
     * @param {import("@web/core/file_viewer/file_viewer").FileViewer.props.files} files
     * @param {Function} [onCloseCallback]
     */
    function open(file, files = [file], onCloseCallback) {
        closeFn?.();
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
                    close: () => closeFn?.(),
                },
                {
                    rootId: owner?.root?.el?.getRootNode()?.host?.id,
                    onRemove: onCloseCallback,
                }
            );
        }
    }
    return { open, close: () => closeFn?.() };
}
>>>>>>> c47db30432003f92b6b62993bdad5ce8abe257ba

export function useFileViewer() {
    const owner = useComponent();
    const createFileViewer = useService("fileViewer");
    const { open, close } = createFileViewer(owner);
    onWillDestroy(close);
    return { open, close };
}
