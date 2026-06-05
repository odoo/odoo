import { Component, onPatched } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useRef } from "@web/owl2/utils";
import { SectionDropdown } from "../section_dropdown/section_dropdown";

export class SectionRow extends Component {
    static template = "account.SectionRow";

    static components = { SectionRow, SectionDropdown };

    static props = {
        isSubsection: Boolean,
        section: Object,
        state: Object,
        selectedSection: Object,
    };

    setup() {
        this.InputRef = useRef("InputRef");

        onPatched(() => {
            if (this.props.state.addingSectionTarget || this.props.state.renamingSectionId) {
                this.InputRef.el?.focus();
            }
        });
    }

    get hasChildren() {
        return this.props.section.children.length;
    }

    get isSelected() {
        return this.props.selectedSection.sectionId == this.props.section.id;
    }

    onSectionLabelKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "Enter" || hotkey === " ") {
            ev.preventDefault();
            this.env.setSelectedSection(this.props.section.id, this.props.selectedSection.filtered);
        }
    }
}
