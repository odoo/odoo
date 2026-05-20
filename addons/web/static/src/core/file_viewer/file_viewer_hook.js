import { onWillDestroy } from "@odoo/owl";
import { FileViewer } from "./file_viewer";
import { useService } from "../utils/hooks";
import { useComponent } from "@web/owl2/utils";
import { registry } from "@web/core/registry";

const fileViewerService = {
    dependencies: ["overlay"],
    start(_env, { overlay }) {
        return (owner) => {
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
        };
    },
};
registry.category("services").add("fileViewer", fileViewerService);

export function useFileViewer() {
    const owner = useComponent();
    const createFileViewer = useService("fileViewer");
    const { open, close } = createFileViewer(owner);
    onWillDestroy(close);
    return { open, close };
}
