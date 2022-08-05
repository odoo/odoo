/** @odoo-module **/

import { ColorList } from "@web/core/colorlist/colorlist";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useTooltip } from "@web/core/tooltip/tooltip_hook";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { Field } from "@web/views/fields/field";
import { fileTypeMagicWordMap, imageCacheKey } from "@web/views/fields/image/image_field";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { evalDomain } from "../utils";
import { KANBAN_BOX_ATTRIBUTE, KANBAN_TOOLTIP_ATTRIBUTE } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanCoverImageDialog } from "./kanban_cover_image_dialog";

const { Component, onMounted, onWillUpdateProps, useRef, xml } = owl;
const { COLORS } = ColorList;

const formatters = registry.category("formatters");

// These classes determine whether a click on a record should open it.
const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action"].join(",");
const ALLOW_GLOBAL_CLICK = [".oe_kanban_global_click", ".oe_kanban_global_click_edit"].join(",");

/**
 * Returns the class name of a record according to its color.
 */
function getColorClass(value) {
    return `oe_kanban_color_${getColorIndex(value)}`;
}

/**
 * Returns the index of a color determined by a given record.
 */
function getColorIndex(value) {
    if (typeof value === "number") {
        return Math.round(value) % COLORS.length;
    } else if (typeof value === "string") {
        const charCodeSum = [...value].reduce((acc, _, i) => acc + value.charCodeAt(i), 0);
        return charCodeSum % COLORS.length;
    } else {
        return 0;
    }
}

/**
 * Returns the proper translated name of a record color.
 */
function getColorName(value) {
    return COLORS[getColorIndex(value)];
}

/**
 * Returns the image URL of a given field on the record.
 *
 * @param {Record} record
 * @param {string} [model] model name
 * @param {string} [field] field name
 * @param {number | [number, ...any[]]} [idOrIds] id or array
 *      starting with the id of the desired record.
 * @param {string} [placeholder] fallback when the image does not
 *  exist
 * @returns {string}
 */
function getImageSrcFromRecordInfo(record, model, field, idOrIds, placeholder) {
    const id = (Array.isArray(idOrIds) ? idOrIds[0] : idOrIds) || null;
    const isCurrentRecord =
        record.resModel === model && (record.resId === id || (!record.resId && !id));
    const fieldVal = record.data[field];
    if (isCurrentRecord && fieldVal && !isBinSize(fieldVal)) {
        // Use magic-word technique for detecting image type
        const type = fileTypeMagicWordMap[fieldVal[0]];
        return `data:image/${type};base64,${fieldVal}`;
    } else if (placeholder && (!model || !field || !id || !fieldVal)) {
        // Placeholder if either the model, field, id or value is missing or null.
        return placeholder;
    } else {
        // Else: fetches the image related to the given id.
        return url("/web/image", {
            model,
            field,
            id,
            unique: imageCacheKey(record.data.__last_update),
        });
    }
}

/**
 * Returns a "raw" version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {any}
 */
function getRawValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    switch (field.type) {
        case "one2many":
        case "many2many": {
            return value.count ? value.currentIds : [];
        }
        case "many2one": {
            return (value && value[0]) || false;
        }
        case "date":
        case "datetime": {
            return value && value.toJSDate();
        }
        default: {
            return value;
        }
    }
}

/**
 * Returns a formatted version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {string}
 */
function getValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    const formatter = formatters.get(field.type, String);
    return formatter(value, { field, data: record.data });
}

function isBinSize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

/**
 * Checks if a html content is empty. If there are only formatting tags
 * with style attributes or a void content. Famous use case is
 * '<p style="..." class=".."><br></p>' added by some web editor(s).
 * Note that because the use of this method is limited, we ignore the cases
 * like there's one <img> tag in the content. In such case, even if it's the
 * actual content, we consider it empty.
 *
 * @param {string} innerHTML
 * @returns {boolean} true if no content found or if containing only formatting tags
 */
function isHtmlEmpty(innerHTML = "") {
    const div = Object.assign(document.createElement("div"), { innerHTML });
    return div.innerText.trim() === "";
}

export class KanbanRecord extends Component {
    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.user = useService("user");

        const { archInfo, Compiler, templates } = this.props;
        const { arch } = archInfo;
        const ViewCompiler = Compiler || KanbanCompiler;

        this.templates = useViewCompiler(ViewCompiler, arch, templates, KANBAN_BOX_ATTRIBUTE);

        if (KANBAN_TOOLTIP_ATTRIBUTE in templates) {
            useTooltip("root", {
                info: this,
                template: this.templates[KANBAN_TOOLTIP_ATTRIBUTE],
            });
        }

        this.createRecordAndWidget(this.props);
        this.rootRef = useRef("root");
        onMounted(() => {
            // FIXME: this needs to be changed to an attribute on the root node...
            this.allowGlobalClick = !!this.rootRef.el.querySelector(ALLOW_GLOBAL_CLICK);
        });
        onWillUpdateProps(this.createRecordAndWidget);
    }

    /**
     * Assigns both "record" and "widget" properties on the kanban record.
     *
     * @param {Object} props
     */
    createRecordAndWidget(props) {
        const { archInfo, list, record } = props;
        const { activeActions } = archInfo;

        // Record
        this.record = Object.create(null);
        for (const fieldName in record.data) {
            this.record[fieldName] = {
                get value() {
                    return getValue(record, fieldName);
                },
                get raw_value() {
                    return getRawValue(record, fieldName);
                },
            };
        }

        // Widget
        const deletable = activeActions.delete && (!list.groupedBy || !list.groupedBy("m2m"));
        const editable = archInfo.activeActions.edit;
        this.widget = {
            deletable,
            editable,
            isHtmlEmpty,
        };
    }

    evalDomainFromRecord(record, expr) {
        return evalDomain(expr, record.evalContext);
    }

    getRecordClasses() {
        const { archInfo, canResequence, forceGlobalClick, group, record } = this.props;
        const classes = ["o_kanban_record"];
        if (canResequence) {
            classes.push("o_record_draggable");
        }
        if (forceGlobalClick || archInfo.openAction) {
            classes.push("oe_kanban_global_click");
        }
        if (group && record.model.hasProgressBars) {
            const progressBar = group.findProgressValueFromRecord(record);
            classes.push(`oe_kanban_card_${progressBar.color}`);
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(getColorClass(value));
        }
        if (record.model.useSampleModel) {
            classes.push("o_sample_data_disabled");
        }
        return classes.join(" ");
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        const { archInfo, forceGlobalClick, openRecord, record } = this.props;
        if (!forceGlobalClick && archInfo.openAction) {
            this.action.doActionButton({
                name: archInfo.openAction.action,
                type: archInfo.openAction.type,
                resModel: record.resModel,
                resId: record.resId,
                resIds: record.resIds,
                context: record.context,
                onClose: async () => {
                    await record.model.root.load();
                    record.model.notify();
                },
            });
        } else if (forceGlobalClick || this.allowGlobalClick) {
            openRecord(record);
        }
    }

    async selectColor(colorIndex) {
        const { archInfo, record } = this.props;
        await record.update({ [archInfo.colorField]: colorIndex });
        await record.save();
    }

    /**
     * @param {Object} params
     */
    triggerAction(params) {
        const env = this.env;
        const { archInfo, group, list, openRecord, record } = this.props;
        const { type } = params;
        switch (type) {
            case "edit": {
                return openRecord(record, "edit");
            }
            case "open": {
                return openRecord(record);
            }
            case "delete": {
                const listOrGroup = group || list;
                if (listOrGroup.deleteRecords) {
                    this.dialog.add(ConfirmationDialog, {
                        body: env._t("Are you sure you want to delete this record?"),
                        confirm: () => listOrGroup.deleteRecords([record]),
                        cancel: () => {},
                    });
                } else {
                    // static list case
                    listOrGroup.removeRecord(record);
                }
                return;
            }
            case "set_cover": {
                const { autoOpen, fieldName } = params;
                const { widget } = archInfo.fieldNodes[fieldName];
                const field = record.fields[fieldName];
                if (
                    field.type === "many2one" &&
                    field.relation === "ir.attachment" &&
                    widget === "attachment_image"
                ) {
                    this.dialog.add(KanbanCoverImageDialog, { autoOpen, fieldName, record });
                } else {
                    const warning = sprintf(
                        env._t(
                            `Could not set the cover image: incorrect field ("%s") is provided in the view.`
                        ),
                        fieldName
                    );
                    this.notification.add({ title: warning, type: "danger" });
                }
                break;
            }
            default: {
                return this.notification.add(env._t("Kanban: no action for type: ") + type, {
                    type: "danger",
                });
            }
        }
    }

    //-------------------------------------------------------------------------
    // KANBAN SPECIAL GETTERS AND FUNCTIONS
    //
    // Note: the names of these getters and functions answer to outdated standards
    // but should not be altered for the sake of compatibility.
    //-------------------------------------------------------------------------

    get context() {
        return this.props.record.context;
    }

    get luxon() {
        return luxon;
    }

    get JSON() {
        return JSON;
    }

    get read_only_mode() {
        return this.props.readonly;
    }

    get selection_mode() {
        return this.props.forceGlobalClick;
    }

    get user_context() {
        return this.user.context;
    }

    kanban_color() {
        return getColorClass(...arguments);
    }

    kanban_getcolor() {
        return getColorIndex(...arguments);
    }

    kanban_getcolorname() {
        return getColorName(...arguments);
    }

    kanban_image() {
        return getImageSrcFromRecordInfo(this.props.record, ...arguments);
    }
}

KanbanRecord.components = {
    Dropdown,
    DropdownItem,
    Field,
    KanbanCoverImageDialog,
    ViewButton,
    Widget,
};
KanbanRecord.defaultProps = {
    colors: COLORS,
    openRecord: () => {},
};
KanbanRecord.props = [
    "archInfo",
    "canResequence?",
    "colors?",
    "Compiler?",
    "forceGlobalClick?",
    "group?",
    "list",
    "openRecord?",
    "readonly?",
    "record",
    "templates",
];
KanbanRecord.template = xml`
    <div
        role="article"
        t-att-class="getRecordClasses()"
        t-att-data-id="props.canResequence and props.record.id"
        t-att-tabindex="props.record.model.useSampleModel ? -1 : 0"
        t-on-click="onGlobalClick"
        t-ref="root">
        <t t-call="{{ templates['${KANBAN_BOX_ATTRIBUTE}'] }}"/>
    </div>`;
