import { _t } from "@web/core/l10n/translation";
import {
    sectionNoteListField,
    SectionListRenderer,
    SectionNoteListField,
} from "@web/views/fields/section_note_list/section_note_list_field";
import { registry } from "@web/core/registry";
import { mergeClasses } from "@web/core/utils/classname";

export class SaleSectionListRenderer extends SectionListRenderer {
    static recordRowTemplate = "sale.SectionListRenderer.Row";

    setup(){
        super.setup();
        this.pricesColumns = ['price_unit', 'price_subtotal', 'price_total', 'discount'];
    }

    _papaSaysHide(hierarchyItem, key) {
        if (hierarchyItem.isTopSection) {
            return false;
        }

        if (hierarchyItem.isSubSection && !hierarchyItem.parent.isRoot) {
            return hierarchyItem.parent?.record.data[key];
        }

        if (hierarchyItem.isRecord || hierarchyItem.isNote) {
            const parent = hierarchyItem.parent;
            if (!parent || parent.isRoot) return false;

            if (parent.isTopSection) {
                return parent.record.data[key];
            }

            if (parent.isSubSection) {
                return parent.parent.isTopSection
                    ? parent.parent.record.data[key] || parent.record.data[key]
                    : parent.record.data[key];
            }
        }

        return false;
    }

    getDropDownItems(hierarchyItem) {
        return [
            {
                id: "toggleComposition",
                label: hierarchyItem.record.data.hide_composition ? _t("Show Composition") : _t("Hide Composition"),
                icon: hierarchyItem.record.data.hide_composition ? "fa-eye" : "fa-eye-slash",
                onSelected: async () => {
                    const changes = { hide_composition: !hierarchyItem.record.data.hide_composition };
                    await hierarchyItem.record.update(changes);
                },
            },
            {
                id: "togglePrices",
                label: hierarchyItem.record.data.hide_prices ? _t("Show Prices") : _t("Hide Prices"),
                icon: hierarchyItem.record.data.hide_prices ? "fa-eye" : "fa-eye-slash",
                onSelected: async () => {
                    const changes = { hide_prices: !hierarchyItem.record.data.hide_prices };
                    await hierarchyItem.record.update(changes);
                },
            },
        ];
    }

    getRowClass(record) {
        const item = this.getHierarchyItem(record.id);
        const cssClass = super.getRowClass(record);
        if (this._papaSaysHide(item, 'hide_composition')) {
            return mergeClasses(cssClass, `text-muted`);
        }
        return cssClass;
    }

    getSectionRowClass(record) {
        const section = this.getHierarchyItem(record.id);
        const cssClass = super.getSectionRowClass(record);
        if (this._papaSaysHide(section, 'hide_composition')) {
            return mergeClasses(cssClass, `text-muted`);
        }
        return cssClass;
    }

    getNoteRowClass(record) {
        const item = this.getHierarchyItem(record.id);
        const cssClass = super.getNoteRowClass(record);
        if (this._papaSaysHide(item, 'hide_composition')) {
            return mergeClasses(cssClass, `text-muted`);
        }
        return cssClass;
    }

    getCellClass(column, record) {
        const cssClass = super.getCellClass(column, record);
        if (this.pricesColumns.includes(column.name)) {
            const item = this.getHierarchyItem(record.id);
            if (this._papaSaysHide(item, 'hide_prices')) {
                return mergeClasses(cssClass, `text-muted`);
            }
        }
        return cssClass;
    }
}

export class SaleSectionNoteListField extends SectionNoteListField {
    static components = {
        ...super.components,
        ListRenderer: SaleSectionListRenderer,
    };
}

export const saleSectionNoteListField = {
    ...sectionNoteListField,
    component: SaleSectionNoteListField,
};

registry
    .category("fields")
    .add("sale_section_note_list", saleSectionNoteListField);
