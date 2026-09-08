import { Component, onMounted, onPatched, onWillUnmount, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { UrlField, urlField } from "@web/views/fields/url/url_field";
import { PageDependencies } from "@website/components/dialog/page_properties";
import { TranslationButton } from "@web/views/fields/translation/translation_button";

/**
 * Displays website page dependencies and URL redirect options when the page URL
 * is updated.
 */
class PageUrlField extends UrlField {
    static components = { PageDependencies, TranslationButton };
    static template = "website.PageUrlField";
    // Inlined from UrlField's static props (UrlField is not yet converted to
    // an exported schema const; it has no defaultProps of its own).
    props = useProps({
        ...standardFieldProps,
        placeholder: t.string().optional(),
        text: t.string().optional(),
        websitePath: t.boolean().optional(true),
    });

    setup() {
        super.setup();
        this.serverUrl = `${window.location.origin}/`;
        this.uiService = useService("ui");

        // Trigger onchange api on input event to display redirection
        // parameters as soon as the user types.
        // TODO should find a way to do this more automatically (and option in
        // the framework? or at least a t-on-input?)
        let cleanup;
        let listenedEl;
        const setupInputListener = () => {
            const inputEl = this.inputRef();
            if (inputEl === listenedEl) {
                return;
            }
            if (cleanup) {
                cleanup();
                cleanup = undefined;
            }
            listenedEl = inputEl;
            if (inputEl) {
                const originalValue = inputEl.value;
                let previousValueChanged = false;
                const fireChangeEvent = debounce(() => {
                    const currentValue = inputEl.value;
                    const valueChanged = currentValue !== originalValue;
                    if (valueChanged !== previousValueChanged) {
                        if (currentValue[0] !== "/") {
                            inputEl.value = `/${currentValue}`;
                        }
                        inputEl.dispatchEvent(new Event("change"));
                        inputEl.value = currentValue;
                        previousValueChanged = valueChanged;
                    }
                }, 100);
                inputEl.addEventListener("input", fireChangeEvent);
                cleanup = () => {
                    inputEl.removeEventListener("input", fireChangeEvent);
                };
            }
        };
        onMounted(setupInputListener);
        onPatched(setupInputListener);
        onWillUnmount(() => cleanup && cleanup());
    }

    get value() {
        let value = super.value;
        // Strip leading slash
        if (value[0] === "/") {
            value = value.substring(1);
        }
        // Re-add the leading slash for saving, because url field is required
        // and thus doesn't accept an empty string.
        this.props.record.data[this.props.name] = `/${value.trim()}`;
        return value;
    }
    get isTranslatable() {
        return this.props.record.fields[this.props.name].translate;
    }
}

const pageUrlField = {
    ...urlField,
    component: PageUrlField,
};

registry.category("fields").add("page_url", pageUrlField);

/**
 * Displays 'Selection' field's values as images to select.
 * Image src for each value can be added using the option 'images' on field XML.
 */
export class ImageRadioField extends Component {
    static template = "website.FieldImageRadio";
    props = useProps({
        ...standardFieldProps,
        images: t.array(t.string()),
    });

    setup() {
        const selection = this.props.record.fields[this.props.name].selection;
        // Check if value / label exists for each selection item and add the
        // corresponding image from field options.
        this.values = selection
            .filter((item) => item[0] || item[1])
            .map((value, index) => [
                ...value,
                (this.props.images && this.props.images[index]) || "",
            ]);
    }

    /**
     * @param {String} value
     */
    onSelectValue(value) {
        this.props.record.update({ [this.props.name]: value });
    }
}

export const imageRadioField = {
    component: ImageRadioField,
    supportedOptions: [
        {
            label: _t("Images"),
            name: "images",
            type: "string",
            help: _t("Use an array to list the images to use in the radio selection."),
        },
    ],
    supportedTypes: ["selection"],
    extractProps: ({ options }) => ({
        images: options.images,
    }),
};

registry.category("fields").add("image_radio", imageRadioField);
