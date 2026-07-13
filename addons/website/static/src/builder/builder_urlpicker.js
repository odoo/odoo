import { BuilderUrlPicker } from "@html_builder/core/building_blocks/builder_urlpicker";
import { useActionInfo } from "@html_builder/core/utils";
import { props, t } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import wUtils from "@website/js/utils";

export class AutoCompleteBuilderUrlPicker extends AutoComplete {
<<<<<<< e66104c5bff5b7ffcf5cd11db997b1b0313914ec
    builderProps = props({
        inputClass: t.string().optional(),
    });
||||||| 4dbcc72ecf4ddfdc481714c6471b962c9612b4c5
    static props = {
        ...AutoComplete.props,
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
        inputClass: { type: String, optional: true },
    };
=======
    static props = {
        ...AutoComplete.props,
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
        inputClass: { type: String, optional: true },
        previewButton: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...AutoComplete.defaultProps,
        previewButton: true,
    };
>>>>>>> e0729fdbcbbeaa0a2488dff2ee6a5a9897b39677
    static template = "website.AutoCompleteBuilderUrlPicker";

    setup() {
        super.setup();
        this.info = useActionInfo();
    }

    get ulDropdownClass() {
        return `${super.ulDropdownClass} dropdown-menu ui-autocomplete o_website_ui_autocomplete`;
    }
}

patch(BuilderUrlPicker, {
    components: { ...BuilderUrlPicker.components, AutoCompleteBuilderUrlPicker },
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
        this.commit(value);
        // Forces the input to update its value even if the value of the
        // element in the DOM has not changed.
        this.state.value = null;
        this.state.value = value;
    },

    onChange({ inputValue, isOptionSelected }) {
        if (isOptionSelected) {
            return;
        }
        const normalizedDisplayValue = this.commit(inputValue);
        this.urlRef.el.value = normalizedDisplayValue;
    },

    openPreviewUrl() {
        if (this.urlRef.el.value) {
            window.open(this.urlRef.el.value, "_blank");
        }
    },
});
