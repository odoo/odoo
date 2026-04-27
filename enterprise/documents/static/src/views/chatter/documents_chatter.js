import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useService } from "@web/core/utils/hooks";

export class DocumentsChatter extends Chatter {
    setup() {
        super.setup();
        this.documentService = useService("document.document");
    }

    /**
     * @override
     */
    onActivityChanged(thread) {
        super.onActivityChanged(thread);
        this.documentService.bus.trigger("DOCUMENT_CHATTER_ACTIVITY_CHANGED", {
            recordId: thread.id,
        });
    }
}
