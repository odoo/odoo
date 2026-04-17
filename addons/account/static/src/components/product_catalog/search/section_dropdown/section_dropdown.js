import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from '@web/core/network/rpc';
import { _t } from '@web/core/l10n/translation';

export class SectionDropdown extends Component {
    static template = "account.SectionDropdown";
    static components = { Dropdown, DropdownItem };

    static props = {
        section: Object,
        state: Object,
    };

    async duplicateSection() {
        const result = await rpc("/product/catalog/duplicate_section",
            this.env._getSectionInfoParams({
                section_id: this.props.section.id,
                parent_id: this.props.section.parent_id,
            })
        );

        const section = JSON.parse(JSON.stringify(this.props.section));
        section.id = result.id;
        if (this.props.section.parent_id) {
            this.parent.children.push(section);
            this.parent.isOpen = true;
        } else {
            this.props.state.sections.push(section);
        }
        const sequenceMap = result.sections;

        const update = (sections) => {
            for (const s of sections) {
                if (sequenceMap[s.id] !== undefined) {
                    s.sequence = sequenceMap[s.id];
                }
                if (s.children?.length) {
                    update(s.children);
                }
            }
        };
        update(this.props.state.sections);
        this.env._sortSectionsBySequence(this.props.state.sections);
        this.env.setSelectedSection(section.id);
    }

    async deleteSection() {
        const { section, state } = this.props;

        await rpc(
            "/product/catalog/delete_section",
            this.env._getSectionInfoParams({ section_id: section.id })
        );

        const remove = (sections) => {
            for (let i = 0; i < sections.length; i++) {
                const s = sections[i];

                if (s.id === section.id) {
                    sections.splice(i, 1);
                    return true;
                }

                if (s.children?.length && remove(s.children)) {
                    return true;
                }
            }
            return false;
        };

        remove(state.sections);

        const selected = this.env.searchModel.selectedSection.sectionId;

        if (selected === section.id) {
            this.env.setSelectedSection(state.sections[0]?.id || null, false);
        }

        if (!state.sections.length) {
            state.sections.push({
                id: false,
                name: _t("No Section"),
                line_count: 0,
                children: [],
                isOpen: true,
            });
            this.env.setSelectedSection(false, false);
        }
    }

    async toggleFieldOfSection(field) {
        const section = this.props.section;

        await rpc(
            "/product/catalog/toggle_field_of_section",
            this.env._getSectionInfoParams({
                section_id: section.id,
                field: field,
            })
        );
        section[field] = !section[field];

        // If enabled, disable others
        if (section[field]) {

            for (const f of this._getToggleFieldsOfSection()) {
                if (f !== field) {
                    section[f] = false;
                }
            }
        }
    }

    disableCompositionButton() {
        return !!this.parent?.collapse_composition;
    }

    disablePricesButton() {
        return !!(this.parent?.collapse_prices || this.parent?.collapse_composition);
    }

    get parent() {
        return this.env._findSectionById(
            this.props.section.parent_id,
            this.props.state.sections
        );
    }

    _getToggleFieldsOfSection(){
        return ["collapse_prices", "collapse_composition"];
    }
}
