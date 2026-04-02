import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from '@web/core/network/rpc';
import { _t } from '@web/core/l10n/translation';

export class SectionsDropdown extends Component {
    static template = "account.SectionsDropdown";
    static components = { Dropdown, DropdownItem };

    static props = {
        section: Object,
        state: Object,
    };

    async duplicateSection() {
        const result = await rpc("/product/catalog/duplicate_section",
            this._getSectionInfoParams({
                section_id: this.props.section.id,
                parent_id: this.props.section.parent_id,
            })
        );

        const section = JSON.parse(JSON.stringify(this.props.section));
        section.id = result.id;
        if (this.props.section.parent_id) {
            const parent = this.env._findSectionById(this.props.section.parent_id, this.props.state.sections);
            parent.children.push(section);
            parent.isOpen = true;
        } else {
            this.props.state.sections.push(section);
        }
        const sequenceMap = result.sections;

        const update = (list) => {
            for (const s of list) {
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
            this._getSectionInfoParams({ section_id: section.id })
        );

        const remove = (list) => {
            for (let i = 0; i < list.length; i++) {
                const s = list[i];

                if (s.id === section.id) {
                    list.splice(i, 1);
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
            this.env.setSelectedSection(
                state.sections[0]?.id || null,
                false
            );
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

    _getSectionInfoParams(extra = {}) {
        const ctx = this.env.model.config.context;
        return {
            res_model: ctx.product_catalog_order_model,
            order_id: ctx.order_id,
            child_field: ctx.child_field,
            ...extra,
        };
    }
}
