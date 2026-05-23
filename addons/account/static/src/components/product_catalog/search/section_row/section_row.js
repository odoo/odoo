import { Component, onPatched } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useRef } from "@web/owl2/utils";
import { SectionDropdown } from "../section_dropdown/section_dropdown";

export class SectionRow extends Component {
    static template = "account.SectionRow";

    static components = { SectionRow, SectionDropdown };

    static props = {
        section: Object,
        state: Object,
        selectedSection: Object,
    };

    setup() {
        this.InputRef = useRef("InputRef");

        onPatched(() => {
            if (this.props.state.isAddingSection || this.props.state.renamingSectionId) {
                this.InputRef.el?.focus();
            }
        });
    }

    onSectionLabelKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "Enter" || hotkey === " ") {
            ev.preventDefault();
            this.env.setSelectedSection(this.props.section.id, this.props.selectedSection.filtered);
        }
    }
}
