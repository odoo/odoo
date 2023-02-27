/** @odoo-module **/

import { isMobileOS } from "@web/core/browser/feature_detection";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TagsList } from "../many2many_tags/tags_list";
import { onMounted, useRef, useState } from "@odoo/owl";

export class Many2ManyTagsAvatarField extends Many2ManyTagsField {
    static template = "web.Many2ManyTagsAvatarField";
    static components = {
        Many2XAutocomplete,
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
    extractProps: (fieldInfo) => ({
        ...many2ManyTagsField.extractProps(fieldInfo),
        withCommand: fieldInfo.viewType === "form",
    }),
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
        deleteTag: { type: Function },
        updateTag: { type: Function },
    };

    setup() {
        super.setup();
        this.state = useState({ tags: this.tags });
        this.update = async (recordList) => {
            const updatedVal = await this.props.updateTag(recordList);
            this.state.tags = updatedVal.map((tag) => ({
                ...tag,
                onDelete: () => this.deleteTag(tag.id),
            }));
        };
        onMounted(() => {
            this.autoCompleteRef.el.querySelector("input").focus();
        });
    }
    async deleteTag(id) {
        const updatedVal = await this.props.deleteTag(id);
        this.state.tags = updatedVal.map((tag) => ({
            ...tag,
            onDelete: () => this.deleteTag(tag.id),
        }));
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
        this.popover = usePopover();
        this.emptyAvatar = useRef("emptyAvatar");
    }
    get visibleTagsCount() {
        return this.props.itemsVisible;
    }
    closePopover() {
        this.closePopoverFn();
        this.closePopoverFn = null;
    }
    openPopover(ev) {
        if (this.props.readonly) {
            return;
        }
        if (this.closePopoverFn) {
            this.closePopover();
        }
        this.emptyAvatar.el?.dispatchEvent(new MouseEvent("mouseleave"));
        this.emptyAvatar.el?.removeAttribute("data-tooltip-template");
        this.closePopoverFn = this.popover.add(
            ev.currentTarget.parentElement,
            Many2ManyTagsAvatarFieldPopover,
            {
                ...this.props.popoverProps,
                readonly: false,
                canCreate: false,
                canCreateEdit: false,
                canQuickCreate: false,
            },
            {
                position: "bottom",
                onClose: () => {
                    this.emptyAvatar.el?.setAttribute(
                        "data-tooltip-template",
                        "web.TagsList.Tooltip"
                    );
                },
            }
        );
    }

    get canDisplayDelete() {
        return !this.props.readonly && !isMobileOS();
    }
}

export class KanbanMany2ManyTagsAvatarField extends Many2ManyTagsAvatarField {
    static template = "web.KanbanMany2ManyTagsAvatarField";
    static components = {
        ...Many2ManyTagsAvatarField.component,
        TagsList: KanbanMany2ManyTagsAvatarFieldTagsList,
    };
    itemsVisible = 2;

    get isFieldReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }

    get popoverProps() {
        return {
            ...this.props,
            readonly: this.isFieldReadonly,
            deleteTag: this.deleteTag.bind(this),
            updateTag: this.updateTag.bind(this),
        };
    }
    async deleteTag(id) {
        super.deleteTag(id);
        await this.props.record.save({ noReload: true });
        return this.tags;
    }
    async updateTag(recordList) {
        await this.update(recordList);
        await this.props.record.save({ noReload: true });
        return this.tags;
    }

    getTagProps(record) {
        return {
            ...super.getTagProps(record),
            onDelete: () => this.deleteTag(record.id),
        };
    }
}

export const kanbanMany2ManyTagsAvatarField = {
    ...many2ManyTagsAvatarField,
    component: KanbanMany2ManyTagsAvatarField,
};

registry.category("fields").add("kanban.many2many_tags_avatar", kanbanMany2ManyTagsAvatarField);
