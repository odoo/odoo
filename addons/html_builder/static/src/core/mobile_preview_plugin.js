import { Plugin } from "@html_editor/plugin";

export class MobilePreviewPlugin extends Plugin {
    static id = "mobilePreview";

    resources = {
        device_view_switched_handlers: [
            // ({ isMobileView: boolean }) => {
            //      called on switch between previewing a small screen and a large screen
            // }
        ],
    };

    setup() {
        this.isMobileView = this.config.isMobileView(this.editable);
        this.observer = new ResizeObserver(() => {
            const isMobileView = this.config.isMobileView(this.editable);
            if (this.isMobileView !== isMobileView) {
                this.isMobileView = isMobileView;
                this.dispatchTo("device_view_switched_handlers", { isMobileView });
            }
        });
        this.observer.observe(this.editable);
    }

    destroy() {
        this.observer.disconnect();
    }
}
