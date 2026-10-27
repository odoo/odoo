import { useOnChange } from "@odoo/owl";
import { FileViewer } from "@web/core/file_viewer/file_viewer";
import { patch } from "@web/core/utils/patch";

patch(FileViewer.prototype, {
    setup() {
        super.setup(...arguments);
        useOnChange(
            () => [this.state.file],
            (file) => {
                if (!file.isCloudTextInViewer) {
                    return;
                }
                const controller = new AbortController();
                file.loadCloudText(controller.signal).then(() => {
                    if (!controller.signal.aborted && !file.cloudTextUrl) {
                        this.state.isIframeLoaded = true;
                    }
                });
                return () => {
                    controller.abort();
                    file.unloadCloudText();
                };
            }
        );
    },
    onIframeLoaded() {
        if (this.state.file.isCloudTextInViewer && !this.state.file.cloudTextUrl) {
            return;
        }
        super.onIframeLoaded(...arguments);
    },
});
