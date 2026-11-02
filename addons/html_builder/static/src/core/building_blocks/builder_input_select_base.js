import { BuilderSelect } from "@html_builder/core/building_blocks/builder_select";

export class BuilderInputSelectBase extends BuilderSelect {
    /**
     * Closes the dropdown when Enter or Tab key is pressed.
     *
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        if (ev.key === "Enter" || ev.key === "Tab") {
            this.dropdown.close();
        }
    }

    /**
     * Opens the dropdown when clicked.
     */
    onClick() {
        this.dropdown.open();
    }
}
