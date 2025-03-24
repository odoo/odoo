import { CopyClipboardCharField } from "@web/views/fields/copy_clipboard/copy_clipboard_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { CharField } from "@web/views/fields/char/char_field";

class RecruitmentCopyClipboardCharField extends CopyClipboardCharField {
    static template = "hr_recruitment.RecruitmentCopyClipboardCharField";
    static components = { Field: CharField, CopyButton };
}
export const recruitmentCopyClipboardCharField = {
    component: RecruitmentCopyClipboardCharField,
    displayName: _t("Copy to Clipboard"),
    supportedTypes: ["char"],
};
registry.category("fields").add("RecruitmentCopyClipboardCharField", recruitmentCopyClipboardCharField);
