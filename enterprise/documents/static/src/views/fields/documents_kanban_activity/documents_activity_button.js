import { ActivityButton } from "@mail/core/web/activity_button";
import { useService } from "@web/core/utils/hooks";

export class DocumentsActivityButton extends ActivityButton {
    setup() {
        super.setup();
        this.documentService = useService("document.document");
    }

    /**
     * @override
     */
    onActivityChanged() {
        this.documentService.bus.trigger("DOCUMENT_ACTIVITY_CHANGED", {
            recordId: this.props.record.data.id,
        });
        super.onActivityChanged();
    }
}
