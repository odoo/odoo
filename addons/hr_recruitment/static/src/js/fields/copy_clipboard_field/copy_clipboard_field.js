import { CopyClipboardCharField, copyClipboardCharField } from "@web/views/fields/copy_clipboard/copy_clipboard_field";
import { CharField } from "@web/views/fields/char/char_field";
import { GenerateContentAndCopyButton } from "../../buttons/generate_content_and_copy_button";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class RecruitmentCopyClipboardCharField extends CopyClipboardCharField {
    static template = "hr_recruitment.RecruitmentCopyClipboardCharField";
    static components = { Field: CharField, GenerateContentAndCopyButton };
    static props = {
        ...CopyClipboardCharField.props,
        contentGenerationFunctionName: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    get contentGenerationFunction() {
        if(this.props.contentGenerationFunctionName) {
            return () => this.orm.call(
                this.props.record._config.resModel,
                this.props.contentGenerationFunctionName,
                [this.props.record.resId],
            );
        }
        return null;
    }
}

export const recruitmentCopyClipboardCharField = {
    ...copyClipboardCharField,
    component: RecruitmentCopyClipboardCharField,
    displayName: _t("Copy to Clipboard"),
    supportedTypes: ["char"],
    extractProps({ options }) {
        const props = copyClipboardCharField.extractProps(...arguments);
        props.contentGenerationFunctionName = options.contentGenerationFunctionName;
        return props;
    },
};
registry.category("fields").add("RecruitmentCopyClipboardCharField", recruitmentCopyClipboardCharField);
