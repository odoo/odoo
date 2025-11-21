import { _t } from "@web/core/l10n/translation";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { ColorList } from "@web/core/colorlist/colorlist";
import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import {
    Many2XAutocomplete,
    useActiveActions,
    useX2ManyCrud,
    useOpenMany2XRecord,
} from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { standardFieldProps } from "../standard_field_props";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { TagsList } from "@web/core/tags_list/tags_list";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";

import { Component, useRef } from "@odoo/owl";
import { getFieldDomain } from "@web/model/relational_model/utils";

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
        Tag: BadgeTag,
        TagsList,
        Many2XAutocomplete,
        Popover: Many2ManyTagsFieldColorListPopover,
    };
    static props = {
        ...standardFieldProps,
        canCreate: { type: Boolean, optional: true },
        canQuickCreate: { type: Boolean, optional: true },
        canCreateEdit: { type: Boolean, optional: true },
        onTagClick: {
            optional: true,
            validate(value) {
                return ["open_form", "edit_color"].includes(value);
            },
        },
        colorField: { type: String, optional: true },
        createExpression: { type: String, optional: true },
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

    visibleItemsLimit = Number.POSITIVE_INFINITY;

    setup() {
        this.orm = useService("orm");
        this.previousColorsMap = {};
        this.popover = usePopover(this.constructor.components.Popover);
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
            true
        );

        this.activeActions = useActiveActions({
            fieldType: "many2many",
            crudOptions: {
                create: this.props.canCreate && this.props.createExpression,
                createEdit: this.props.canCreateEdit,
                onDelete: removeRecord,
                edit: this.props.record.isInEdition,
            },
            getEvalParams: (props) => ({
                evalContext: this.evalContext,
                readonly: props.readonly,
            }),
        });

        this.openMany2xRecord = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions: {
                create: false,
                write: true,
            },
            onRecordSaved: (record) => {
                const records = this.props.record.data[this.props.name].records;
                return records.find((r) => r.resId === record.resId).load();
            },
        });

        this.update = (recordlist) => {
            recordlist = recordlist
                ? recordlist.filter(
                      (element) => !this.tags.some((record) => record.resId === element.id)
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

    get tagsListProps() {
        return {
            mapTooltip: (tag) => tag.props.tooltip,
            tags: this.tags,
            visibleItemsLimit: this.visibleItemsLimit,
        };
    }

    getTagProps(record) {
        return {
            color: record.data[this.props.colorField],
            onDelete: !this.props.readonly ? () => this.deleteTag(record.id) : undefined,
            text: record.data.display_name || "",
            tooltip: record.data.display_name || "",
            onClick: (ev) => this.onTagClick(ev, record),
        };
    }

    onTagClick(ev, record) {
        if (!this.props.record.isInEdition) {
            return;
        }
        if (this.props.onTagClick === "open_form") {
            return this.openMany2xRecord({
                resId: record.resId,
                context: this.props.context,
                title: _t("Edit: %s", record.data.display_name),
            });
        }
        if (this.props.onTagClick !== "edit_color" || !this.props.colorField) {
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

    async onTagVisibilityChange(isHidden, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id
        );
        if (tagRecord.data[this.props.colorField] !== 0) {
            this.previousColorsMap[tagRecord.resId] = tagRecord.data[this.props.colorField];
        }
        const changes = {
            [this.props.colorField]: isHidden ? 0 : this.previousColorsMap[tagRecord.resId] || 1,
        };
        await tagRecord.update(changes);
        await tagRecord.save();
        this.popover.close();
    }

    get tags() {
        return this.props.record.data[this.props.name].records.map((record) => ({
            id: record.id,
            props: this.getTagProps(record),
        }));
    }

    get showM2OSelectionField() {
        return !this.props.readonly;
    }

    async deleteTagByIndex(index) {
        this.mutex.exec(() => {
            if (this.tags[index]) {
                return this.deleteTag(this.tags[index].id);
            }
        });
    }

    async deleteTag(id) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === id
        );
        await this.props.record.data[this.props.name].forget(tagRecord);
    }

    getDomain() {
        return Domain.and([
            getFieldDomain(this.props.record, this.props.name, this.props.domain),
        ]).toList(this.props.context);
    }

    isSelected(record) {
        const records = this.props.record.data[this.props.name].records;
        return records.some((r) => r.resId === record.id);
    }

    async switchTagColor(colorIndex, tag) {
        const tagRecord = this.props.record.data[this.props.name].records.find(
            (record) => record.id === tag.id
        );
        await tagRecord.update({ [this.props.colorField]: colorIndex });
        await tagRecord.save();
        this.popover.close();
    }
}

export const many2ManyTagsField = {
    component: Many2ManyTagsField,
    displayName: _t("Tags"),
    supportedTypes: ["many2many", "one2many"],
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
            isRelationalField: true,
            availableTypes: ["integer"],
            help: _t("Set an integer field to use colors with the tags."),
        },
        {
            label: _t("Typeahead search"),
            name: "search_threshold",
            type: "number",
            help: _t(
                "Defines the minimum number of characters to perform the search. If not set, the search is performed on focus."
            ),
        },
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
        {
            label: _t("On tag click"),
            name: "on_tag_click",
            type: "selection",
            choices: [
                { label: "", value: "" },
                { label: _t("Edit color"), value: "edit_color" },
                { label: _t("Open form"), value: "open_form" },
            ],
            help: _t(
                "Defines the behavior when a tag is clicked. 'Edit color' requires a color field"
            ),
        },
    ],
    relatedFields: ({ options }) => {
        const relatedFields = [{ name: "display_name", type: "char" }];
        if (options.color_field) {
            relatedFields.push({ name: options.color_field, type: "integer", readonly: false });
        }
        return relatedFields;
    },
    extractProps({ attrs, options, string, placeholder }, dynamicInfo) {
        const hasCreatePermission = attrs.can_create ? evaluateBooleanExpr(attrs.can_create) : true;
        const hasEditPermission = attrs.can_write ? evaluateBooleanExpr(attrs.can_write) : true;
        const noCreate = Boolean(options.no_create);
        const canCreate = noCreate ? false : hasCreatePermission;
        const noQuickCreate = Boolean(options.no_quick_create);
        const noCreateEdit = Boolean(options.no_create_edit);
        const props = {
            colorField: options.color_field,
            nameCreateField: options.create_name_field,
            canCreate,
            canQuickCreate: canCreate && !noQuickCreate,
            canCreateEdit: canCreate && !noCreateEdit,
            createExpression: attrs.create,
            context: dynamicInfo.context,
            domain: dynamicInfo.domain,
            placeholder,
            searchThreshold: options.search_threshold,
            string,
        };
        let onTagClick = false;
        if (options.on_tag_click === "open_form" && hasEditPermission) {
            onTagClick = "open_form";
        } else if (
            options.on_tag_click === "edit_color" &&
            hasEditPermission &&
            options.color_field
        ) {
            onTagClick = "edit_color";
        }
        if (onTagClick) {
            props.onTagClick = onTagClick;
        }
        return props;
    },
};

registry.category("fields").add("many2many_tags", many2ManyTagsField);
registry.category("fields").add("calendar.one2many", many2ManyTagsField);
registry.category("fields").add("calendar.many2many", many2ManyTagsField);
