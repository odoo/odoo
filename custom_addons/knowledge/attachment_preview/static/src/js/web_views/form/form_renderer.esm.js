import {AttachmentPreviewWidget} from "../../attachmentPreviewWidget.esm";
import {FormRenderer} from "@web/views/form/form_renderer";
import {patch} from "@web/core/utils/patch";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        this.mailComponents = {
            ...this.mailComponents,
            AttachmentPreviewWidget,
        };
    },
});
