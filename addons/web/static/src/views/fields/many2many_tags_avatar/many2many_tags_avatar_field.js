import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { AvatarTag } from "@web/core/tags_list/avatar_tag";
import { imageUrl } from "@web/core/utils/urls";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    static template = "web.Many2ManyTagsAvatarField";
    static optionTemplate = "web.Many2ManyTagsAvatarField.option";
    static components = {
        ...super.components,
        Tag: AvatarTag,
    };
    static props = {
        ...Many2ManyTagsField.props,
        withCommand: { type: Boolean, optional: true },
    };

    get assignBtnTooltip() {
        return _t("Assign");
    }

    get specification() {
        return {};
    }

    getTagProps(record) {
        return {
            imageUrl: imageUrl(this.relation, record.resId, "avatar_128", {
                unique: record.data.write_date,
            }),
            onDelete: !this.props.readonly ? () => this.deleteTag(record.id) : undefined,
            text: record.data.display_name,
            tooltip: record.data.display_name,
        };
    }
}

export const many2ManyTagsAvatarField = {
    ...many2ManyTagsField,
    component: Many2ManyTagsAvatarField,
    relatedFields: (fieldInfo) => {
        const relatedFields = many2ManyTagsField.relatedFields(fieldInfo);
        relatedFields.push({ name: "write_date", type: "datetime" });
        return relatedFields;
    },
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

export class KanbanMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    static props = {
        ...super.props,
        isEditable: { type: Boolean, optional: true },
    };
    visibleItemsLimit = 3;

    setup() {
        super.setup();
        this.popover = usePopover(Many2ManyTagsAvatarFieldPopover, {
            popoverClass: "o_m2m_tags_avatar_field_popover",
            closeOnClickAway: (target) => !target.closest(".modal"),
        });
    }

    get canDisplayQuickAssignAvatar() {
        return this.props.isEditable;
    }

    get popoverProps() {
        const props = { ...this.props };
        delete props.isEditable;
        return props;
    }

    get tags() {
        return super.tags.reverse();
    }

    openPopover(ev) {
        this.popover.open(ev.currentTarget.parentElement, {
            ...this.popoverProps,
            readonly: false,
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            placeholder: _t("Search users..."),
        });
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
