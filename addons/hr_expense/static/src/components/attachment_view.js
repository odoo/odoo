import { patch } from "@web/core/utils/patch";
import { AttachmentView } from "@mail/core/common/attachment_view";
import { onMounted } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

patch(AttachmentView.prototype, {
    get displayName() {
        if (this.state.thread.model === 'hr.expense') {
            return this.state.thread.message_main_attachment_id.res_name || this.state.thread.name;
        }
        return super.displayName;
    }
});

export class ExpenseAttachment extends AttachmentView {
    static props = [...AttachmentView.props, "openInPopout"];
    static components = { AttachmentView };

    setup() {
        super.setup();
        if (this.props.openInPopout) {
            onMounted(this.onClickPopout);
        }
        // In the mail_popout_service.js the function pollClosedWindow will trigger a resize event on the main window
        // when the external window is closed. It allows us to know when to hide the preview for small screens.
        useBus(this.uiService.bus, "resize", () => this.env.setPopout(false));
    }
}
