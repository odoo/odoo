import { Component, onMounted, onPatched, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class SectionRow extends Component {
    static template = "account.SectionRow";
    static components = { Dropdown, DropdownItem, SectionRow };

    props = useProps({
        children: t.array().optional([]),
        id: t.or([t.boolean(), t.number()]).optional(),
        name: t.string(),
        parent_id: t.or([t.boolean(), t.number()]).optional(false),
        subtotal: t.number().optional(0),
        isOpen: t.boolean().optional(false),
        editing: t.boolean().optional(false),
    });

    InputRef = signal(null);

    setup() {
        onMounted(() => {
            // New (sub)section
            if (this.props.editing) {
                this.InputRef()?.focus();
            }
        });
        onPatched(() => {
            // Renaming (sub)section
            if (this.props.editing) {
                this.InputRef()?.focus();
            }
        });
    }

    get isSelected() {
        return this.env.searchModel.selectedSectionId === this.props.id;
    }

    get isFiltered() {
        return this.env.searchModel.filterBySection && this.isSelected;
    }

    get isSection() {
        return !this.isSubsection;
    }

    get isSubsection() {
        return !!this.props.parent_id;
    }

    get hasChildren() {
        return this.props.children.length;
    }

    onSectionLabelKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "Enter" || hotkey === " ") {
            ev.preventDefault();
            this.env.setSelectedSection(this.props.id);
        }
    }
}
