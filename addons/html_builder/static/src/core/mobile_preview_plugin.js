import { Plugin } from "@html_editor/plugin";

/**
 * @typedef {((args: {isMobileView: boolean}) => ())[]} device_view_switched_handlers
 * called on switch between previewing a small screen and a large screen
 */

export class MobilePreviewPlugin extends Plugin {
    static id = "mobilePreview";

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
        super.destroy();
        this.observer.disconnect();
    }
}
