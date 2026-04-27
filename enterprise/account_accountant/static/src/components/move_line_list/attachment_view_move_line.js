import { AttachmentView } from "@mail/core/common/attachment_view";
import { onMounted } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export class AttachmentViewMoveLine extends AttachmentView {
    static props = [...AttachmentView.props, "openInPopout"];
    static components = { AttachmentView };

    setup() {
        super.setup();
        if (this.props.openInPopout) {
            onMounted(this.onClickPopout);
        }
        // In the mail_popout_service.js the function pollClosedWindow will trigger a resize event on the main window
        // when the external window is closed. It allow us to know when to hide the preview for small screens.
        useBus(this.uiService.bus, "resize", () => this.env.setPopout(false));
    }
}
