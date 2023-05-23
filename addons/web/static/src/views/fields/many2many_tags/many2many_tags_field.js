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
import { TagsList } from "@web/core/tags_list/tags_list";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

import { Component, useRef } from "@odoo/owl";

class Many2ManyTagsFieldColorListPopover extends Component {
    static template = "web.Many2ManyTagsFieldColorListPopover";
    static components = {
        CheckBox,
        ColorList,
    };
}

export class Many2ManyTagsField extends Component {
    static template = "web.Many2ManyTagsField";
    static components = {
        TagsList,
        Many2XAutocomplete,
    };
    static props = {
        ...standardFieldProps,
        canCreate: { type: Boolean, optional: true },
        canQuickCreate: { type: Boolean, optional: true },
        canCreateEdit: { type: Boolean, optional: true },
        colorField: { type: String, optional: true },
        createDomain: { type: [Array, Boolean], optional: true },
        domain: { type: [Array, Function], optional: true },
        context: { type: Object, optional: true },
        placeholder: { type: String, optional: true },
        nameCreateField: { type: String, optional: true },
        string: { type: String, optional: true },
        noViewAll: { type: Boolean, optional: true },
    };
    static defaultProps = {
        canCreate: true,
        canQuickCreate: true,
        canCreateEdit: true,
        nameCreateField: "name",
        context: {},
    };

    static RECORD_COLORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    static SEARCH_MORE_LIMIT = 320;

    setup() {
        this.orm = useService("orm");
        this.previousColorsMap = {};
        this.popover = usePopover(this.constructor.components.Popover);
        this.dialog = useService("dialog");
        this.dialogClose = [];

        this.autoCompleteRef = useRef("autoComplete");

        const { saveRecord, removeRecord } = useX2ManyCrud(
            () => this.props.record.data[this.props.name],
            true
        );

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
                const created = await this.orm.call(this.relation, "name_create", [name], {
                    context: this.props.context,
                });
                return saveRecord([created[0]]);
            };
        }
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }
    get evalContext() {
        return this.props.record.evalContext;
    }
    get string() {
        return this.props.string || this.props.record.fields[this.props.name].string || "";
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
        return this.props.record.data[this.props.name].records.map((record) =>
            this.getTagProps(record)
        );
    }

    get showM2OSelectionField() {
        return !this.props.readonly;
    }

    deleteTag(id) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === id
        );
        const ids = this.props.record.data[this.props.name].currentIds.filter(
            (id) => id !== tagRecord.resId
        );
        this.props.record.data[this.props.name].replaceWith(ids);
    }

    getDomain() {
        const domain =
            typeof this.props.domain === "function" ? this.props.domain() : this.props.domain;
        return Domain.and([
            domain,
            Domain.not([["id", "in", this.props.record.data[this.props.name].currentIds]]),
        ]).toList(this.props.context);
    }

    focusTag(index) {
        const autoCompleteParent = this.autoCompleteRef.el.parentElement;
        const tags = autoCompleteParent.getElementsByClassName("o_tag");
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
        const tags = [...autoCompleteParent.getElementsByClassName("o_tag")];
        const closestTag = ev.target.closest(".o_tag");
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

export const many2ManyTagsField = {
    component: Many2ManyTagsField,
    displayName: _lt("Tags"),
    supportedOptions: [
        {
            label: _lt("Disable creation"),
            name: "no_create",
            type: "boolean",
        },
        {
            label: _lt("Use colors"),
            name: "color_field",
            type: "boolean",
        },
    ],
    supportedTypes: ["many2many"],
    isSet: (value) => value.count > 0,
    relatedFields: ({ options }) => {
        const relatedFields = [{ name: "display_name", type: "char" }];
        if (options.color_field) {
            relatedFields.push({ name: options.color_field, type: "integer" });
        }
        return relatedFields;
    },
    extractProps({ attrs, options, string }, dynamicInfo) {
        const noCreate = Boolean(options.no_create);
        const canCreate = attrs.can_create && Boolean(JSON.parse(attrs.can_create)) && !noCreate;
        const noQuickCreate = Boolean(options.no_quick_create);
        const noCreateEdit = Boolean(options.no_create_edit);
        return {
            colorField: options.color_field,
            nameCreateField: options.create_name_field,
            canCreate,
            canQuickCreate: canCreate && !noQuickCreate,
            canCreateEdit: canCreate && !noCreateEdit,
            createDomain: options.create,
            context: dynamicInfo.context,
            domain: dynamicInfo.domain,
            placeholder: attrs.placeholder,
            string,
        };
    },
};

registry.category("fields").add("many2many_tags", many2ManyTagsField);
registry.category("fields").add("calendar.one2many", many2ManyTagsField);
registry.category("fields").add("calendar.many2many", many2ManyTagsField);

/**
 * A specialization that allows to edit the color with the colorpicker.
 * Used in form view.
 */
export class Many2ManyTagsFieldColorEditable extends Many2ManyTagsField {
    static components = {
        ...super.components,
        Popover: Many2ManyTagsFieldColorListPopover,
    };
    static props = {
        ...super.props,
        canEditColor: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...super.defaultProps,
        canEditColor: true,
    };

    getTagProps(record) {
        const props = super.getTagProps(record);
        props.onClick = (ev) => this.onBadgeClick(ev, record);
        return props;
    }

    onBadgeClick(ev, record) {
        if (!this.props.canEditColor) {
            return;
        }
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.popover.open(ev.currentTarget, {
                colors: this.constructor.RECORD_COLORS,
                tag: {
                    id: record.id,
                    colorIndex: record.data[this.props.colorField],
                },
                switchTagColor: this.switchTagColor.bind(this),
                onTagVisibilityChange: this.onTagVisibilityChange.bind(this),
            });
        }
    }

    onTagVisibilityChange(isHidden, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id
        );
        if (tagRecord.data[this.props.colorField] != 0) {
            this.previousColorsMap[tagRecord.resId] = tagRecord.data[this.props.colorField];
        }
        tagRecord.update({
            [this.props.colorField]: isHidden ? 0 : this.previousColorsMap[tagRecord.resId] || 1,
        });
        tagRecord.save();
        this.popover.close();
    }

    switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id
        );
        tagRecord.update({ [this.props.colorField]: colorIndex });
        tagRecord.save();
        this.popover.close();
    }
}

export const many2ManyTagsFieldColorEditable = {
    ...many2ManyTagsField,
    component: Many2ManyTagsFieldColorEditable,
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions,
        {
            label: _lt("Prevent color edition"),
            name: "no_edit_color",
            type: "boolean",
        },
    ],
    extractProps({ options }) {
        const props = many2ManyTagsField.extractProps(...arguments);
        props.canEditColor = !options.no_edit_color && !!options.color_field;
        return props;
    },
};

registry.category("fields").add("form.many2many_tags", many2ManyTagsFieldColorEditable);
