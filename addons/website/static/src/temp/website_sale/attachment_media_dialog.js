import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { useChildSubEnv } from "@odoo/owl";

// Small override of the MediaDialog to retrieve the attachment ids instead of img elements
export class AttachmentMediaDialog extends MediaDialog {
    setup() {
        super.setup();
        useChildSubEnv({ addFieldImage: true });
    }
}
