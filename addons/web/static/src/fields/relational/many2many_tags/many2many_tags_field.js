// @ts-check

/** @module @web/fields/relational/many2many_tags/many2many_tags_field - Colored tag list field with autocomplete for Many2many relations */

import { Component, useRef } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { ColorList } from "@web/components/colorlist/colorlist";
import { useTagNavigation } from "@web/components/record_selectors/tag_navigation_hook";
import { TagsList } from "@web/components/tags_list/tags_list";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { usePopover } from "@web/ui/popover/popover_hook";

import { m2oSupportedOptions } from "../many2one/many2one_field";
import { Many2XAutocomplete, useOpenMany2XRecord } from "../many2x_autocomplete";
import { useActiveActions } from "../relational_active_actions";
import { useX2ManyCrud } from "../x2many_crud";

class Many2ManyTagsFieldColorListPopover extends Component {
    static template = "web.Many2ManyTagsFieldColorListPopover";
    static components = {
        CheckBox,
        ColorList,
    };
    static props = {
        colors: Array,
        tag: Object,
        switchTagColor: Function,
        onTagVisibilityChange: Function,
        close: Function,
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
        searchThreshold: { type: Number, optional: true },
        string: { type: String, optional: true },
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
        this.popover = usePopover(
            /** @type {any} */ (this.constructor).components.Popover,
        );
        this.dialog = useService("dialog");
        this.dialogClose = [];
        useTagNavigation("many2ManyTagsField", {
            isEnabled: () => !this.props.readonly,
            delete: (index) => this.deleteTagByIndex(index),
        });
        this.autoCompleteRef = useRef("autoComplete");
        this.mutex = new Mutex();

        const { saveRecord, removeRecord } = useX2ManyCrud(
            () => this.props.record.data[this.props.name],
            true,
        );

        this.activeActions = useActiveActions({
            fieldType: "many2many",
            crudOptions: {
                create: this.props.canCreate && this.props.createDomain,
                createEdit: this.props.canCreateEdit,
                onDelete: removeRecord,
                edit: this.props.record.isInEdition,
            },
            getEvalParams: (props) => ({
                evalContext: this.evalContext,
                readonly: props.readonly,
            }),
        });

        this.openMany2xRecord = useOpenMany2XRecord(
            /** @type {any} */ ({
                resModel: this.relation,
                activeActions: {
                    create: false,
                    write: true,
                },
                onRecordSaved: (record) => {
                    const records = this.props.record.data[this.props.name].records;
                    return records.find((r) => r.resId === record.resId).load();
                },
            }),
        );

        this.update = (recordlist) => {
            recordlist = recordlist
                ? recordlist.filter(
                      (element) =>
                          !this.tags.some((record) => record.resId === element.id),
                  )
                : [];
            if (!recordlist.length) {
                return;
            }
            const resIds = recordlist.map((rec) => rec.id);
            return saveRecord(resIds);
        };

        if (this.props.canQuickCreate) {
            this.quickCreate = async (name) => {
                const created = await this.orm.call(
                    this.relation,
                    "name_create",
                    [name],
                    {
                        context: this.props.context,
                    },
                );
                return saveRecord([created[0]]);
            };
        }
    }

    /** @returns {string} Co-model name for the relation */
    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }
    /** @returns {Object} Current record's evaluation context */
    get evalContext() {
        return this.props.record.evalContext;
    }
    /** @returns {string} Human-readable field label */
    get string() {
        return (
            this.props.string || this.props.record.fields[this.props.name].string || ""
        );
    }

    /**
     * @param {Object} record - A relational record from the many2many list
     * @returns {{ id: string, resId: number, text: string, colorIndex: number|undefined, canEdit: boolean|undefined, onDelete: Function|undefined }}
     */
    getTagProps(record) {
        return {
            id: record.id, // datapoint_X
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: record.data[this.props.colorField],
            canEdit: this.props.canEditTags,
            onDelete: !this.props.readonly
                ? () => this.deleteTag(record.id)
                : undefined,
        };
    }

    /** @returns {Array<Object>} Tag props for each linked record */
    get tags() {
        return this.props.record.data[this.props.name].records.map((record) =>
            this.getTagProps(record),
        );
    }

    /** @returns {boolean} */
    get showM2OSelectionField() {
        return !this.props.readonly;
    }

    /** @param {number} index - Zero-based index of the tag to delete */
    async deleteTagByIndex(index) {
        this.mutex.exec(() => {
            if (this.tags[index]) {
                return this.deleteTag(this.tags[index].id);
            }
        });
    }

    /** @param {string} id - Datapoint ID of the tag record to remove */
    async deleteTag(id) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === id,
        );
        await this.props.record.data[this.props.name].forget(tagRecord);
    }

    /** @returns {Array} Evaluated domain for the many2many autocomplete search */
    getDomain() {
        return Domain.and([
            getFieldDomain(this.props.record, this.props.name, this.props.domain),
        ]).toList(this.props.context);
    }

    /**
     * @param {{ id: number }} record - Candidate record to check
     * @returns {boolean} Whether the record is already linked
     */
    isSelected(record) {
        const records = this.props.record.data[this.props.name].records;
        return records.some((r) => r.resId === record.id);
    }
}

export const many2ManyTagsField = {
    component: Many2ManyTagsField,
    displayName: _t("Tags"),
    supportedOptions: [
        ...m2oSupportedOptions.filter((o) => o.name !== "no_open"),
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
            isRelationalField: true,
            availableTypes: ["integer"],
            help: _t("Set an integer field to use colors with the tags."),
        },
    ],
    supportedTypes: ["many2many", "one2many"],
    relatedFields: ({ options }) => {
        const relatedFields = [{ name: "display_name", type: "char" }];
        if (options.color_field) {
            relatedFields.push({
                name: options.color_field,
                type: "integer",
                readonly: false,
            });
        }
        return relatedFields;
    },
    extractProps({ attrs, options, string, placeholder }, dynamicInfo) {
        const hasCreatePermission = attrs.can_create
            ? evaluateBooleanExpr(attrs.can_create)
            : true;
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
            placeholder,
            searchThreshold: options.search_threshold,
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
        canEditTags: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...super.defaultProps,
        canEditColor: true,
        canEditTags: false,
    };

    /** @override */
    getTagProps(record) {
        const props = super.getTagProps(record);
        props.onClick = (ev) => this.onTagClick(ev, record);
        return props;
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} record - The tag's relational record
     */
    onTagClick(ev, record) {
        if (this.props.canEditTags) {
            return this.openMany2xRecord({
                resId: record.resId,
                context: this.props.context,
                title: _t("Edit: %s", record.data.display_name),
            });
        }
        if (!this.props.canEditColor) {
            return;
        }
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.popover.open(ev.currentTarget, {
                colors: /** @type {any} */ (this.constructor).RECORD_COLORS,
                tag: {
                    id: record.id,
                    colorIndex: record.data[this.props.colorField],
                },
                switchTagColor: this.switchTagColor.bind(this),
                onTagVisibilityChange: this.onTagVisibilityChange.bind(this),
            });
        }
    }

    /**
     * @param {boolean} isHidden - Whether to hide (color=0) or restore the tag
     * @param {{ id: string }} tag
     */
    async onTagVisibilityChange(isHidden, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id,
        );
        if (tagRecord.data[this.props.colorField] !== 0) {
            this.previousColorsMap[tagRecord.resId] =
                tagRecord.data[this.props.colorField];
        }
        const changes = {
            [this.props.colorField]: isHidden
                ? 0
                : this.previousColorsMap[tagRecord.resId] || 1,
        };
        await tagRecord.update(changes);
        await tagRecord.save();
        this.popover.close();
    }

    /**
     * @param {number} colorIndex - New color index to assign
     * @param {{ id: string }} tag
     */
    async switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id,
        );
        await tagRecord.update({ [this.props.colorField]: colorIndex });
        await tagRecord.save();
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
        {
            label: _t("Edit Tags"),
            name: "edit_tags",
            type: "boolean",
            help: _t(
                "If checked, clicking on the tag will open the form that allows to directly edit it. Note that if a color field is also set, the tag edition will prevail. So, the color picker will not be displayed on click on the tag.",
            ),
        },
    ],
    extractProps({ options, attrs }) {
        const props = many2ManyTagsField.extractProps(...arguments);
        const hasEditPermission = attrs.can_write
            ? evaluateBooleanExpr(attrs.can_write)
            : true;
        props.canEditTags = options.edit_tags ? hasEditPermission : false;
        props.canEditColor =
            !props.canEditTags && !options.no_edit_color && !!options.color_field;
        return props;
    },
};

registry.category("fields").add("form.many2many_tags", many2ManyTagsFieldColorEditable);
