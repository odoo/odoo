/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { ColorList } from "@web/core/colorlist/colorlist";
import { Domain } from "@web/core/domain";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import {
    Many2XAutocomplete,
    useActiveActions,
    useX2ManyCrud,
} from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";
import { TagsList } from "./tags_list";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import { Component, useRef } from "@odoo/owl";

class Many2ManyTagsFieldColorListPopover extends Component {}
Many2ManyTagsFieldColorListPopover.template = "web.Many2ManyTagsFieldColorListPopover";
Many2ManyTagsFieldColorListPopover.components = {
    CheckBox,
    ColorList,
};

export class Many2ManyTagsField extends Component {
    setup() {
        this.orm = useService("orm");
        this.previousColorsMap = {};
        this.popover = usePopover();
        this.dialog = useService("dialog");
        this.dialogClose = [];

        this.autoCompleteRef = useRef("autoComplete");

        const { saveRecord, removeRecord } = useX2ManyCrud(() => this.props.value, true);

        this.activeActions = useActiveActions({
            fieldType: "many2many",
            crudOptions: {
                create: this.props.canCreate && this.props.createDomain,
                createEdit: this.props.canCreateEdit,
                onDelete: removeRecord,
            },
            getEvalParams: (props) => {
                return {
                    evalContext: this.evalContext,
                    readonly: props.readonly,
                };
            },
        });

        this.update = (recordlist) => {
            if (!recordlist) {
                return;
            }
            if (Array.isArray(recordlist)) {
                const resIds = recordlist.map((rec) => rec.id);
                return saveRecord(resIds);
            }
            return saveRecord(recordlist);
        };

        if (this.props.canQuickCreate) {
            this.quickCreate = async (name) => {
                const created = await this.orm.call(this.props.relation, "name_create", [name], {
                    context: this.context,
                });
                return saveRecord([created[0]]);
            };
        }
    }

    get domain() {
        return this.props.record.getFieldDomain(this.props.name);
    }
    get context() {
        return this.props.record.getFieldContext(this.props.name);
    }
    get evalContext() {
        return this.props.record.evalContext;
    }
    get string() {
        return this.props.record.activeFields[this.props.name].string;
    }

    getTagProps(record) {
        return {
            id: record.id, // datapoint_X
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: record.data[this.props.colorField],
            onDelete: !this.props.readonly ? () => this.deleteTag(record.id) : undefined,
            onKeydown: this.onTagKeydown.bind(this),
        };
    }

    get tags() {
        return this.props.value.records.map((record) => this.getTagProps(record));
    }

    get showM2OSelectionField() {
        return !this.props.readonly;
    }

    deleteTag(id) {
        const tagRecord = this.props.value.records.find((record) => record.id === id);
        const ids = this.props.value.currentIds.filter((id) => id !== tagRecord.resId);
        this.props.value.replaceWith(ids);
    }

    getDomain() {
        return Domain.and([
            this.domain,
            Domain.not([["id", "in", this.props.value.currentIds]]),
        ]).toList(this.context);
    }

    focusTag(index) {
        const autoCompleteParent = this.autoCompleteRef.el.parentElement;
        const tags = autoCompleteParent.getElementsByClassName("badge");
        if (tags.length) {
            if (index === undefined) {
                tags[tags.length - 1].focus();
            } else {
                tags[index].focus();
            }
        }
    }

    onAutoCompleteKeydown(ev) {
        if (ev.isComposing) {
            // This case happens with an IME for example: we let it handle all key events.
            return;
        }
        const hotkey = getActiveHotkey(ev);
        const input = ev.target.closest(".o-autocomplete--input");
        const autoCompleteMenuOpened = !!this.autoCompleteRef.el.querySelector(
            ".o-autocomplete--dropdown-menu"
        );
        switch (hotkey) {
            case "arrowleft": {
                if (input.selectionStart || autoCompleteMenuOpened) {
                    return;
                }
                // focus rightmost tag if any.
                this.focusTag();
                break;
            }
            case "arrowright": {
                if (input.selectionStart !== input.value.length || autoCompleteMenuOpened) {
                    return;
                }
                // focus leftmost tag if any.
                this.focusTag(0);
                break;
            }
            case "backspace": {
                if (input.value) {
                    return;
                }
                const tags = this.tags;
                if (tags.length) {
                    const { id } = tags[tags.length - 1];
                    this.deleteTag(id);
                }
                break;
            }
            default:
                return;
        }
        ev.preventDefault();
        ev.stopPropagation();
    }

    onTagKeydown(ev) {
        if (this.props.readonly) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        const autoCompleteParent = this.autoCompleteRef.el.parentElement;
        const tags = [...autoCompleteParent.getElementsByClassName("badge")];
        const closestTag = ev.target.closest(".badge");
        const tagIndex = tags.indexOf(closestTag);
        const input = this.autoCompleteRef.el.querySelector(".o-autocomplete--input");
        switch (hotkey) {
            case "arrowleft": {
                if (tagIndex === 0) {
                    input.focus();
                } else {
                    this.focusTag(tagIndex - 1);
                }
                break;
            }
            case "arrowright": {
                if (tagIndex === tags.length - 1) {
                    input.focus();
                } else {
                    this.focusTag(tagIndex + 1);
                }
                break;
            }
            case "backspace": {
                input.focus();
                const { id } = this.tags[tagIndex] || {};
                this.deleteTag(id);
                break;
            }
            default:
                return;
        }
        ev.preventDefault();
        ev.stopPropagation();
    }
}

Many2ManyTagsField.RECORD_COLORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
Many2ManyTagsField.SEARCH_MORE_LIMIT = 320;

Many2ManyTagsField.template = "web.Many2ManyTagsField";
Many2ManyTagsField.components = {
    TagsList,
    Many2XAutocomplete,
};

Many2ManyTagsField.props = {
    ...standardFieldProps,
    canCreate: { type: Boolean, optional: true },
    canQuickCreate: { type: Boolean, optional: true },
    canCreateEdit: { type: Boolean, optional: true },
    colorField: { type: String, optional: true },
    createDomain: { type: [Array, Boolean], optional: true },
    placeholder: { type: String, optional: true },
    relation: { type: String },
    nameCreateField: { type: String, optional: true },
};
Many2ManyTagsField.defaultProps = {
    canCreate: true,
    canQuickCreate: true,
    canCreateEdit: true,
    nameCreateField: "name",
};

Many2ManyTagsField.displayName = _lt("Tags");
Many2ManyTagsField.supportedTypes = ["many2many"];
Many2ManyTagsField.fieldsToFetch = {
    display_name: { name: "display_name", type: "char" },
};
Many2ManyTagsField.isSet = (value) => value.count > 0;

Many2ManyTagsField.extractProps = ({ attrs, field }) => {
    const noCreate = Boolean(attrs.options.no_create);
    const canCreate = noCreate ? false : attrs.can_create && Boolean(JSON.parse(attrs.can_create));
    const noQuickCreate = Boolean(attrs.options.no_quick_create);
    const noCreateEdit = Boolean(attrs.options.no_create_edit);

    return {
        colorField: attrs.options.color_field,
        nameCreateField: attrs.options.create_name_field,
        relation: field.relation,
        canCreate,
        canQuickCreate: canCreate && !noQuickCreate,
        canCreateEdit: canCreate && !noCreateEdit,
        createDomain: attrs.options.create,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("many2many_tags", Many2ManyTagsField);

/**
 * A specialization that allows to edit the color with the colorpicker.
 * Used in form view.
 */
export class Many2ManyTagsFieldColorEditable extends Many2ManyTagsField {
    getTagProps(record) {
        const props = super.getTagProps(record);
        props.onClick = (ev) => this.onBadgeClick(ev, record);
        return props;
    }

    closePopover() {
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }

    onBadgeClick(ev, record) {
        if (!this.props.canEditColor) {
            return;
        }
        const isClosed = !document.querySelector(".o_tag_popover");
        if (isClosed) {
            this.currentPopoverEl = null;
        }
        if (this.popoverCloseFn) {
            this.closePopover();
        }
        if (isClosed || this.currentPopoverEl !== ev.currentTarget) {
            this.currentPopoverEl = ev.currentTarget;
            this.popoverCloseFn = this.popover.add(
                ev.currentTarget,
                this.constructor.components.Popover,
                {
                    colors: this.constructor.RECORD_COLORS,
                    tag: {
                        id: record.id,
                        colorIndex: record.data[this.props.colorField],
                    },
                    switchTagColor: this.switchTagColor.bind(this),
                    onTagVisibilityChange: this.onTagVisibilityChange.bind(this),
                }
            );
        }
    }

    onTagVisibilityChange(isHidden, tag) {
        const tagRecord = this.props.value.records.find((record) => record.id === tag.id);
        if (tagRecord.data[this.props.colorField] != 0) {
            this.previousColorsMap[tagRecord.resId] = tagRecord.data[this.props.colorField];
        }
        tagRecord.update({
            [this.props.colorField]: isHidden ? 0 : this.previousColorsMap[tagRecord.resId] || 1,
        });
        tagRecord.save();
        this.closePopover();
    }

    switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.value.records.find((record) => record.id === tag.id);
        tagRecord.update({ [this.props.colorField]: colorIndex });
        tagRecord.save();
        this.closePopover();
    }
}

Many2ManyTagsFieldColorEditable.components = {
    ...Many2ManyTagsField.components,
    Popover: Many2ManyTagsFieldColorListPopover,
};
Many2ManyTagsFieldColorEditable.props = {
    ...Many2ManyTagsField.props,
    canEditColor: { type: Boolean, optional: true },
};
Many2ManyTagsFieldColorEditable.defaultProps = {
    ...Many2ManyTagsField.defaultProps,
    canEditColor: true,
};
Many2ManyTagsFieldColorEditable.extractProps = (params) => {
    const props = Many2ManyTagsField.extractProps(params);
    const attrs = params.attrs;
    const noEditColor = Boolean(attrs.options.no_edit_color);
    const hasColorField = Boolean(attrs.options.color_field);
    return {
        ...props,
        canEditColor: !noEditColor && hasColorField,
    };
};

registry.category("fields").add("form.many2many_tags", Many2ManyTagsFieldColorEditable);

registry.category("fields").add("calendar.one2many", Many2ManyTagsField);
registry.category("fields").add("calendar.many2many", Many2ManyTagsField);
