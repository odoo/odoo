/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { ColorList } from "@web/core/colorlist/colorlist";
import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
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
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";

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
        noSearchMore: { type: Boolean, optional: true },
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
        this.onTagKeydown = useTagNavigation(
            "many2ManyTagsField",
            this.deleteTagByIndex.bind(this)
        );
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
            onKeydown: (ev) => {
                if (this.props.readonly) {
                    return;
                }
                this.onTagKeydown(ev);
            },
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

    async deleteTagByIndex(index) {
        const { id } = this.tags[index] || {};
        this.deleteTag(id);
    }

    async deleteTag(id) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === id
        );
        await this.props.record.data[this.props.name].forget(tagRecord);
    }

    getDomain() {
        const domain =
            typeof this.props.domain === "function" ? this.props.domain() : this.props.domain;
        const currentIds = this.props.record.data[this.props.name].currentIds.filter(
            (id) => typeof id === "number"
        );
        return Domain.and([domain, Domain.not([["id", "in", currentIds]])]).toList(
            this.props.context
        );
    }
}

export const many2ManyTagsField = {
    component: Many2ManyTagsField,
    displayName: _t("Tags"),
    supportedOptions: [
        {
            label: _t("Disable creation"),
            name: "no_create",
            type: "boolean",
            help: _t(
                "If checked, users won't be able to create records through the autocomplete dropdown at all."
            ),
        },
        {
            label: _t("Disable 'Create' option"),
            name: "no_quick_create",
            type: "boolean",
            help: _t(
                "If checked, users will not be able to create records based on the text input; they will still be able to create records via a popup form."
            ),
        },
        {
            label: _t("Disable 'Create and Edit' option"),
            name: "no_create_edit",
            type: "boolean",
            help: _t(
                "If checked, users will not be able to create records based through a popup form; they will still be able to create records based on the text input."
            ),
        },
        {
            label: _t("Can create"),
            name: "create",
            type: "string",
            help: _t("Write a domain to allow the creation of records conditionnally."),
        },
        {
            label: _t("Color field"),
            name: "color_field",
            type: "field",
            availableTypes: ["integer"],
            help: _t("Set an integer field to use colors with the tags."),
        },
    ],
    supportedTypes: ["many2many"],
    relatedFields: ({ options }) => {
        const relatedFields = [{ name: "display_name", type: "char" }];
        if (options.color_field) {
            relatedFields.push({ name: options.color_field, type: "integer", readonly: false });
        }
        return relatedFields;
    },
    extractProps({ attrs, options, string }, dynamicInfo) {
        const hasCreatePermission = attrs.can_create ? evaluateBooleanExpr(attrs.can_create) : true;
        const noCreate = Boolean(options.no_create);
        const canCreate = noCreate ? false : hasCreatePermission;
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
        const changes = {
            [this.props.colorField]: isHidden ? 0 : this.previousColorsMap[tagRecord.resId] || 1,
        };
        tagRecord.update(changes, { save: true });
        this.popover.close();
    }

    switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id
        );
        tagRecord.update({ [this.props.colorField]: colorIndex }, { save: true });
        this.popover.close();
    }
}

export const many2ManyTagsFieldColorEditable = {
    ...many2ManyTagsField,
    component: Many2ManyTagsFieldColorEditable,
    supportedOptions: [
        ...many2ManyTagsField.supportedOptions,
        {
            label: _t("Prevent color edition"),
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
