/** @odoo-module native */
import {
    CopyClipboardCharField,
    copyClipboardCharField,
} from "@web/fields/basic/copy_clipboard/copy_clipboard_field";
import { CharField } from "@web/fields/basic/char/char_field";
import { CopyButton } from "@web/components/copy_button";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/collections/objects";
import { _t } from "@web/core/translation";
import { registry } from "@web/core/registry";

class RecruitmentCopyClipboardCharField extends CopyClipboardCharField {
    static template = "hr_recruitment.RecruitmentCopyClipboardCharField";
    static components = { Field: CharField, CopyButton };
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
        return omit(
            super.fieldProps,
            "displayedValue",
            "contentGenerationFunctionName",
        );
    }

    /**
     * `CopyButton` awaits a function-valued `content`, so the value is
     * generated on click without a component of our own.
     *
     * @returns {(() => Promise<string>) | null}
     */
    get contentGenerationFunction() {
        if (this.props.contentGenerationFunctionName) {
            return () =>
                this.orm.call(
                    this.props.record.resModel,
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
registry
    .category("fields")
    .add("RecruitmentCopyClipboardChar", recruitmentCopyClipboardCharField);
