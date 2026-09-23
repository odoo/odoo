// @ts-check
/** @odoo-module native */

import { TagsList } from "@web/components/tags_list/tags_list";
import { _t } from "@web/core/translation";
import { shallowEqual } from "@web/core/utils/collections/objects";
import { imageUrl } from "@web/core/utils/urls";
import { registerField } from "@web/fields/_registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/fields/relational/many2many_tags/many2many_tags_field";
import { usePopover } from "@web/ui/popover";

const EMPTY_SPECIFICATION = Object.freeze({});

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    static template = "web.Many2ManyTagsAvatarField";
    static optionTemplate = "web.Many2ManyTagsAvatarField.option";
    static props = {
        ...Many2ManyTagsField.props,
        withCommand: { type: Boolean, optional: true },
    };

    /** @returns {Object} */
    get specification() {
        return EMPTY_SPECIFICATION;
    }

    /**
     * @override
     * @returns {Object}
     */
    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            specification: this.specification,
        };
    }

    /**
     * @override
     * @param {any} record
     */
    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            img: imageUrl(this.relation, record.resId, "avatar_128"),
        };
    }
}

export const many2ManyTagsAvatarField = {
    ...many2ManyTagsField,
    component: Many2ManyTagsAvatarField,
    extractProps: (/** @type {any} */ fieldInfo, /** @type {any} */ dynamicInfo) => ({
        ...many2ManyTagsField.extractProps(fieldInfo, dynamicInfo),
        withCommand: ["form", "list"].includes(fieldInfo.viewType),
    }),
};

registerField("many2many_tags_avatar", many2ManyTagsAvatarField);

export class ListMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    visibleItemsLimit = 5;
}

export const listMany2ManyTagsAvatarField = {
    ...many2ManyTagsAvatarField,
    component: ListMany2ManyTagsAvatarField,
};

registerField(
    { name: "many2many_tags_avatar", view: "list" },
    listMany2ManyTagsAvatarField,
);

export class Many2ManyTagsAvatarFieldPopover extends Many2ManyTagsAvatarField {
    static template = "web.Many2ManyTagsAvatarFieldPopover";
    static props = {
        ...Many2ManyTagsAvatarField.props,
        close: { type: Function },
    };

    /**
     * @override
     * @param {any} recordList
     */
    async update(recordList) {
        await super.update(recordList);
        await this._saveUpdate();
    }

    /**
     * @override
     * @param {string} id
     */
    async removeTag(id) {
        await super.removeTag(id);
        await this._saveUpdate();
    }

    async _saveUpdate() {
        await this.props.record.save({ reload: false });
        this.autoCompleteRef.el?.querySelector("input")?.click();
    }

    /** @returns {Array<Object>} */
    get tags() {
        return super.tags.toReversed();
    }
}

export class KanbanMany2ManyTagsAvatarFieldTagsList extends TagsList {
    static template = "web.KanbanMany2ManyTagsAvatarFieldTagsList";

    static props = {
        ...TagsList.props,
        popoverProps: { type: Object },
        readonly: { type: Boolean, optional: true },
    };
    setup() {
        super.setup();
        this.popover = usePopover(Many2ManyTagsAvatarFieldPopover, {
            class: "o_m2m_tags_avatar_field_popover",
            closeOnClickAway: (target) => !target.closest(".modal"),
        });
    }

    /** @param {MouseEvent} ev */
    openPopover(ev) {
        if (this.props.readonly) {
            return;
        }
        this.popover.open(/** @type {HTMLElement} */ (ev.currentTarget).parentElement, {
            ...this.props.popoverProps,
            readonly: false,
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            placeholder: _t("Search users..."),
        });
    }
    /** @returns {boolean} */
    get canDisplayQuickAssignAvatar() {
        return !this.props.readonly;
    }
}

export class KanbanMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    static template = "web.KanbanMany2ManyTagsAvatarField";
    static components = {
        ...Many2ManyTagsAvatarField.components,
        TagsList: KanbanMany2ManyTagsAvatarFieldTagsList,
    };
    static props = {
        ...Many2ManyTagsAvatarField.props,
        isEditable: { type: Boolean, optional: true },
    };
    visibleItemsLimit = 3;

    /** @type {Record<string, any> | null} */
    _popoverProps = null;

    /** @returns {Object} */
    get popoverProps() {
        const props = { ...this.props, readonly: false };
        delete props.isEditable;
        if (this._popoverProps && shallowEqual(this._popoverProps, props)) {
            return this._popoverProps;
        }
        this._popoverProps = props;
        return props;
    }
    /** @returns {Array<Object>} */
    get tags() {
        return super.tags.toReversed();
    }
}

export const kanbanMany2ManyTagsAvatarField = {
    ...many2ManyTagsAvatarField,
    component: KanbanMany2ManyTagsAvatarField,
    extractProps: (/** @type {any} */ fieldInfo, /** @type {any} */ dynamicInfo) => ({
        ...many2ManyTagsAvatarField.extractProps(fieldInfo, dynamicInfo),
        isEditable: !dynamicInfo.readonly,
    }),
};

registerField(
    { name: "many2many_tags_avatar", view: "kanban" },
    kanbanMany2ManyTagsAvatarField,
);
