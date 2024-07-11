/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "@web/core/tags_list/tags_list";
import { AvatarMany2XAutocomplete } from "@web/views/fields/relational_utils";

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    static template = "web.Many2ManyTagsAvatarField";
    static components = {
        Many2XAutocomplete: AvatarMany2XAutocomplete,
        TagsList,
    };
    static props = {
        ...Many2ManyTagsField.props,
        withCommand: { type: Boolean, optional: true },
    };
    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            img: `/web/image/${this.relation}/${record.resId}/avatar_128`,
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
    itemsVisible = 5;
}

export const listMany2ManyTagsAvatarField = {
    ...many2ManyTagsAvatarField,
    component: ListMany2ManyTagsAvatarField,
};

registry.category("fields").add("list.many2many_tags_avatar", listMany2ManyTagsAvatarField);

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

    async deleteTag(id) {
        await super.deleteTag(id);
        await this._saveUpdate();
    }

    async _saveUpdate() {
        await this.props.record.save({ reload: false });
        // manual render to dirty record
        this.render();
        // update dropdown
        this.autoCompleteRef.el?.querySelector("input")?.click();
    }

    get tags() {
        return super.tags.reverse();
    }
}

export const many2ManyTagsAvatarFieldPopover = {
    ...many2ManyTagsAvatarField,
    component: Many2ManyTagsAvatarFieldPopover,
};
registry.category("fields").add("many2many_tags_avatar_popover", many2ManyTagsAvatarFieldPopover);

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
    get visibleTagsCount() {
        return this.props.itemsVisible;
    }
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
    get canDisplayQuickAssignAvatar() {
        return !this.props.readonly && !(this.props.tags && this.otherTags.length);
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
    itemsVisible = 2;

    get popoverProps() {
        const props = {
            ...this.props,
            readonly: false,
        };
        delete props.isEditable;
        return props;
    }
    get tags() {
        return super.tags.reverse();
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

registry.category("fields").add("kanban.many2many_tags_avatar", kanbanMany2ManyTagsAvatarField);
