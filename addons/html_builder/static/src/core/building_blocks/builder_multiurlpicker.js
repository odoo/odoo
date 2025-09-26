import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import {
    BuilderTextInputBase,
    textInputBasePassthroughProps,
} from "@html_builder/core/building_blocks/builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

export class BuilderMultiUrlPicker extends Component {
    static template = "html_builder.BuilderMultiUrlPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        this.inputRef = useChildRef();
        useBuilderComponent();
        const { state, commit } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.default,
            formatRawValue: this.formatRawValue,
            parseDisplayValue: this.parseDisplayValue,
        });
        this.commit = commit;
        this.state = state;
        this.unselectUrl = this.unselectUrl.bind(this);
    }

    /**
     * @param {String} rawValue - Raw stringified list of URLs.
     * @returns {String[]} Array of selected URLs.
     */
    formatRawValue(rawValue) {
        return rawValue ? JSON.parse(rawValue) : [];
    }

    /**
     * @param {String[]} displayValue - Array of URLs to stringify.
     * @returns {String} JSON stringified representation of the URL list.
     */
    parseDisplayValue(displayValue) {
        return JSON.stringify(displayValue);
    }

    /**
     * Handles the Enter key event to trigger URL selection.
     *
     * @param {KeyboardEvent} ev - The keyboard event.
     */
    handleEnterKey(ev) {
        if (ev.key === "Enter") {
            this.select();
        }
    }

    /**
     * Handles the selection of a URL from the input field.
     */
    select() {
        const url = this.inputRef.el.value;
        const selectedUrls = this.urls;
        this.inputRef.el.value = ""; // clear the input

        if (!url || selectedUrls.includes(url)) {
            return;
        }

        selectedUrls.push(url);
        this.commit(selectedUrls);
    }

    /**
     * Removes the given URL from the list and commits the updated value.
     *
     * @param {String} url - URL to remove.
     */
    unselectUrl(url) {
        const updatedUrls = this.urls.filter((u) => u !== url);
        this.commit(updatedUrls);
    }

    /**
     * @returns {String[]} Array of URLs currently selected in the picker.
     */
    get urls() {
        return this.formatRawValue(this.state.value);
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
