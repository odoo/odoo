/** @odoo-module native */
import { Component, useEffect, useRef } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { debounce } from "@web/core/utils/timing";
import { UrlField, urlField } from "@web/fields/basic/url/url_field";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { PageDependencies } from "@website/components/dialog/page_properties";

const log = makeLogger("website.field.fields");

class PageUrlField extends UrlField {
    static components = { PageDependencies };
    static template = "website.PageUrlField";
    static defaultProps = {
        ...UrlField.defaultProps,
        websitePath: true,
    };

    setup() {
        super.setup();
        useLifecycleLog(log);
        this.serverUrl = `${window.location.origin}/`;
        this.inputRef = useRef("input");

        useEffect(
            (inputEl) => {
                if (inputEl) {
                    const originalValue = inputEl.value;
                    let previousValueChanged = false;
                    const fireChangeEvent = debounce(() => {
                        const currentValue = inputEl.value;
                        const valueChanged = currentValue !== originalValue;
                        if (valueChanged !== previousValueChanged) {
                            log.logic("PageUrlField dispatch change", {
                                valueChanged,
                                currentValue,
                            });
                            if (currentValue[0] !== "/") {
                                inputEl.value = `/${currentValue}`;
                            }
                            inputEl.dispatchEvent(new Event("change"));
                            inputEl.value = currentValue;
                            previousValueChanged = valueChanged;
                        }
                    }, 100);

                    inputEl.addEventListener("input", fireChangeEvent);
                    log.lifecycle("PageUrlField input listener attached");
                    return () => {
                        log.lifecycle("PageUrlField input listener removed");
                        inputEl.removeEventListener("input", fireChangeEvent);
                    };
                }
            },
            () => [this.inputRef.el],
        );
    }

    get value() {
        let value = super.value;
        if (value[0] === "/") {
            value = value.substring(1);
        }
        return value;
    }

    parse(value) {
        // Re-add the leading slash for saving, because url field is required
        // and thus doesn't accept an empty string.
        return `/${value.trim()}`;
    }
}

const pageUrlField = {
    ...urlField,
    component: PageUrlField,
};

registry.category("fields").add("page_url", pageUrlField);

export class ImageRadioField extends Component {
    static template = "website.FieldImageRadio";
    static props = {
        ...standardFieldProps,
        images: { type: Array, element: String },
    };

    setup() {
        useLifecycleLog(log);
        const selection = this.props.record.fields[this.props.name].selection;
        this.values = selection
            .filter((item) => item[0] || item[1])
            .map((value, index) => [
                ...value,
                (this.props.images && this.props.images[index]) || "",
            ]);
        log.pipeline("ImageRadioField values", () => ({
            values: this.values.length,
            images: this.props.images?.length,
        }));
    }

    /**
     * @param {String} value
     */
    onSelectValue(value) {
        log.logic("ImageRadioField select", () => ({ name: this.props.name, value }));
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
