import { BuilderUrlPicker } from "@html_builder/core/building_blocks/builder_urlpicker";
import { patch } from "@web/core/utils/patch";
import { useChildRef } from "@web/core/utils/hooks";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import wUtils from "@website/js/utils";
import { useActionInfo } from "@html_builder/core/utils";
import { textInputBasePassthroughProps } from "@html_builder/core/building_blocks/builder_input_base";

export class AutoCompleteInBuilderUrlPicker extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        ...textInputBasePassthroughProps,
        inputClass: { type: String, optional: true },
    };
    static template = "website.AutoCompleteInBuilderUrlPicker";

    setup() {
        super.setup();
        this.info = useActionInfo();
    }

    get ulDropdownClass() {
        return `${super.ulDropdownClass} dropdown-menu ui-autocomplete o_website_ui_autocomplete`;
    }

    get inputClass() {
        return this.props.inputClass;
    }

    get inputTitle() {
        return this.props.title;
    }
}

patch(BuilderUrlPicker, {
    components: { ...BuilderUrlPicker.components, AutoCompleteInBuilderUrlPicker },
});

patch(BuilderUrlPicker.prototype, {
    setup() {
        super.setup();
        this.urlRef = useChildRef();
    },

    get sources() {
        const body = this.env.getEditingElement().ownerDocument.body;
        return [
            {
                placeholder: _t("Loading..."),
                options: (term) => wUtils.loadOptionsSource(term, body, this.onSelect.bind(this)),
                optionSlot: "urlOption",
            },
        ];
    },

    onSelect(value) {
        this.urlRef.el.value = value;
        this.commit(value);
    },

    onChange(req) {
        this.commit(req.inputValue);
    },

    openPreviewUrl() {
        if (this.urlRef.el.value) {
            window.open(this.urlRef.el.value, "_blank");
        }
    },
});
