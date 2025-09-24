import { PageDependencies } from "@website/components/dialog/page_properties";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { UrlField, urlField } from "@web/views/fields/url/url_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Component, useEffect, useRef } from "@odoo/owl";

/**
 * Displays website page dependencies and URL redirect options when the page URL
 * is updated.
 */
class PageUrlField extends UrlField {
    static components = { PageDependencies };
    static template = "website.PageUrlField";
    static defaultProps = {
        ...UrlField.defaultProps,
        websitePath: true,
    };

    setup() {
        super.setup();
        this.serverUrl = `${window.location.origin}/`;
        this.inputRef = useRef("input");

        // Trigger onchange api on input event to display redirection
        // parameters as soon as the user types.
        // TODO should find a way to do this more automatically (and option in
        // the framework? or at least a t-on-input?)
        useEffect(
            (inputEl) => {
                if (inputEl) {
                    const fireChangeEvent = () => {
                        inputEl.dispatchEvent(new Event("change"));
                    };

                    inputEl.addEventListener("input", fireChangeEvent);
                    return () => {
                        inputEl.removeEventListener("input", fireChangeEvent);
                    };
                }
            },
            () => [this.inputRef.el]
        );
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
    static props = {
        ...standardFieldProps,
        images: { type: Array, element: String },
    };

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
