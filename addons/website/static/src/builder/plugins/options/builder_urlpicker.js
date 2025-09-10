import { patch } from "@web/core/utils/patch";
import { BuilderUrlPicker } from "@html_builder/core/building_blocks/builder_urlpicker";
import { AutoCompleteInLinkPopover, buildOptionsSource } from "@website/js/editor/html_editor";

patch(BuilderUrlPicker, {
    components: { ...BuilderUrlPicker.components, AutoCompleteInLinkPopover },
});

patch(BuilderUrlPicker.prototype, {

    get sources() {
        return [this.optionsSource];
    },

    get optionsSource() {
        return buildOptionsSource(this);
    },

    onSelect(val) {
        this.updateValue(val);
    },

    updateValue(val) {
        this.state.value = val;
        this.commit(val);
    },

    openPreviewUrl() {
        if (this.state.value) {
            window.open(this.state.value, "_blank");
        }
    },
});
