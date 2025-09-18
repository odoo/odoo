// @ts-check

/** @module @web/fields/relational/many2many_tags_avatar/many2many_tags_avatar_field - Avatar tag list field for Many2many relations with user images */

import { TagsList } from "@web/components/tags_list/tags_list";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/fields/relational/many2many_tags/many2many_tags_field";
import { usePopover } from "@web/ui/popover/popover_hook";

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    static template = "web.Many2ManyTagsAvatarField";
    static optionTemplate = "web.Many2ManyTagsAvatarField.option";
    static props = {
        ...Many2ManyTagsField.props,
        withCommand: { type: Boolean, optional: true },
    };

    /** @returns {Object} Empty spec — avatar fields fetch no extra related fields */
    get specification() {
        return {};
    }

    /** @override */
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
    extractProps({ viewType }, dynamicInfo) {
        const props = many2ManyTagsField.extractProps(...arguments);
        props.withCommand = viewType === "form" || viewType === "list";
        props.domain = dynamicInfo.domain;
        return props;
    },
};

registry.category("fields").add("many2many_tags_avatar", many2ManyTagsAvatarField);

export class ListMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    visibleItemsLimit = 5;
}

export const listMany2ManyTagsAvatarField = {
    ...many2ManyTagsAvatarField,
    component: ListMany2ManyTagsAvatarField,
};

registry
    .category("fields")
    .add("list.many2many_tags_avatar", listMany2ManyTagsAvatarField);

export class Many2ManyTagsAvatarFieldPopover extends Many2ManyTagsAvatarField {
    static template = "web.Many2ManyTagsAvatarFieldPopover";
    static props = {
        ...Many2ManyTagsAvatarField.props,
        close: { type: Function },
    };

    setup() {
        super.setup();
        const originalUpdate = this.update;
        this.update = async (recordList) => {
            await originalUpdate(recordList);
            await this._saveUpdate();
        };
    }

    /** @override */
    async deleteTag(id) {
        await super.deleteTag(id);
        await this._saveUpdate();
    }

    /** Persists changes and re-renders the popover dropdown */
    async _saveUpdate() {
        await this.props.record.save({ reload: false });
        // manual render to dirty record
        this.render();
        // update dropdown
        this.autoCompleteRef.el?.querySelector("input")?.click();
    }

    /** @returns {Array<Object>} Tags in reverse order (newest first) */
    get tags() {
        return super.tags.toReversed();
    }
}

export const many2ManyTagsAvatarFieldPopover = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyTagsAvatarFieldPopover,
};
registry
    .category("fields")
    .add("many2many_tags_avatar_popover", many2ManyTagsAvatarFieldPopover);

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
            popoverClass: "o_m2m_tags_avatar_field_popover",
            closeOnClickAway: (target) => !target.closest(".modal"),
        });
    }

    /** @param {MouseEvent} ev */
    openPopover(ev) {
        if (this.props.readonly) {
            return;
        }
        this.popover.open(ev.currentTarget.parentElement, {
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

    /** @returns {Object} Props forwarded to the popover (without isEditable) */
    get popoverProps() {
        const props = {
            ...this.props,
            readonly: false,
        };
        delete props.isEditable;
        return props;
    }
    /** @returns {Array<Object>} Tags in reverse order (newest first) */
    get tags() {
        return super.tags.toReversed();
    }
}

export const kanbanMany2ManyTagsAvatarField = {
    ...many2ManyTagsAvatarField,
    component: KanbanMany2ManyTagsAvatarField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2ManyTagsAvatarField.extractProps(...arguments);
        props.isEditable = !dynamicInfo.readonly;
        return props;
    },
};

registry
    .category("fields")
    .add("kanban.many2many_tags_avatar", kanbanMany2ManyTagsAvatarField);
