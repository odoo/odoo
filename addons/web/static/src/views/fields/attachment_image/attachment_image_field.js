import { Component, usePlugin, useProps } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AttachmentImageField extends Component {
    static template = "web.AttachmentImageField";
    props = useProps({
        ...standardFieldProps,
    });
    debugMode = usePlugin(DebugModePlugin);
}

export const attachmentImageField = {
    component: AttachmentImageField,
    displayName: _t("Attachment Image"),
    supportedTypes: ["many2one"],
};

registry.category("fields").add("attachment_image", attachmentImageField);
