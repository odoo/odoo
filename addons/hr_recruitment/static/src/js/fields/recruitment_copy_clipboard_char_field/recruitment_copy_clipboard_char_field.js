import { CopyClipboardCharField, copyClipboardCharField } from "@web/views/fields/copy_clipboard/copy_clipboard_field";
import { CharField } from "@web/views/fields/char/char_field";
import { GenerateContentAndCopyButton } from "../../buttons/generate_content_and_copy_button";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class RecruitmentCopyClipboardCharField extends CopyClipboardCharField {
    static template = "hr_recruitment.RecruitmentCopyClipboardCharField";
    static components = { Field: CharField, GenerateContentAndCopyButton };
    static props = {
        ...CopyClipboardCharField.props,
        displayedValue: { type: String, optional: true },
        contentGenerationFunctionName: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    get fieldProps() {
        return omit(super.fieldProps, "displayedValue", "contentGenerationFunctionName");
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
        props.displayedValue = options?.displayed_value;
        props.contentGenerationFunctionName = options?.content_generation_function_name;
        return props;
    },
};
registry.category("fields").add("RecruitmentCopyClipboardChar", recruitmentCopyClipboardCharField);
