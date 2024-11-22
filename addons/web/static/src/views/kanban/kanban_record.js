import { _t } from "@web/core/l10n/translation";
import { ColorList } from "@web/core/colorlist/colorlist";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { imageUrl } from "@web/core/utils/urls";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Field } from "@web/views/fields/field";
import { fileTypeMagicWordMap } from "@web/views/fields/image/image_field";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { getFormattedValue } from "../utils";
import { KANBAN_CARD_ATTRIBUTE, KANBAN_MENU_ATTRIBUTE } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanCoverImageDialog } from "./kanban_cover_image_dialog";
import { KanbanDropdownMenuWrapper } from "./kanban_dropdown_menu_wrapper";

import { Component, onWillUpdateProps, useRef, useState } from "@odoo/owl";

const { COLORS } = ColorList;

const formatters = registry.category("formatters");

// These classes determine whether a click on a record should open it.
export const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action", "[data-bs-toggle]"].join(
    ","
);

/**
 * Returns the index of a color determined by a given record.
 */
export function getColorIndex(value) {
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
 * Returns a "raw" version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {any}
 */
export function getRawValue(record, fieldName) {
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
            return value && value.toISO();
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

export function getFormattedRecord(record) {
    const formattedRecord = {
        id: {
            value: record.resId,
            raw_value: record.resId,
        },
    };

    for (const fieldName of record.fieldNames) {
        formattedRecord[fieldName] = {
            value: getValue(record, fieldName),
            raw_value: getRawValue(record, fieldName),
        };
    }
    return formattedRecord;
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
export function getImageSrcFromRecordInfo(record, model, field, idOrIds, placeholder) {
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
        const unique = isCurrentRecord && record.data.write_date;
        return imageUrl(model, id, field, { unique });
    }
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
export function isHtmlEmpty(innerHTML = "") {
    const div = Object.assign(document.createElement("div"), { innerHTML });
    return div.innerText.trim() === "";
}

export class KanbanRecord extends Component {
    static components = {
        Dropdown,
        DropdownItem,
        KanbanDropdownMenuWrapper,
        Field,
        KanbanCoverImageDialog,
        ViewButton,
        Widget,
    };
    static defaultProps = {
        colors: COLORS,
        deleteRecord: () => {},
        archiveRecord: () => {},
        openRecord: () => {},
    };
    static props = [
        "archInfo",
        "canResequence?",
        "colors?",
        "Compiler?",
        "forceGlobalClick?",
        "group?",
        "groupByField?",
        "deleteRecord?",
        "archiveRecord?",
        "openRecord?",
        "readonly?",
        "record",
        "progressBarState?",
    ];
    static Compiler = KanbanCompiler;
    static KANBAN_CARD_ATTRIBUTE = KANBAN_CARD_ATTRIBUTE;
    static KANBAN_MENU_ATTRIBUTE = KANBAN_MENU_ATTRIBUTE;
    static menuTemplate = "web.KanbanRecordMenu";
    static template = "web.KanbanRecord";

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        const { Compiler, archInfo } = this.props;
        const ViewCompiler = Compiler || this.constructor.Compiler;
        const { templateDocs: templates } = archInfo;

        this.templates = useViewCompiler(ViewCompiler, templates);

        this.showMenu = this.constructor.KANBAN_MENU_ATTRIBUTE in templates;

        this.dataState = useState({ record: {}, widget: {} });
        this.createWidget(this.props);
        onWillUpdateProps(this.createWidget);
        useRecordObserver((record) =>
            Object.assign(this.dataState.record, getFormattedRecord(record))
        );
        this.rootRef = useRef("root");
    }

    get record() {
        return this.dataState.record;
    }

    getFormattedValue(fieldId) {
        const { archInfo, record } = this.props;
        const { name } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, archInfo.fieldNodes[fieldId]);
    }

    /**
     * Assigns "widget" properties on the kanban record.
     *
     * @param {Object} props
     */
    createWidget(props) {
        const { archInfo, groupByField } = props;
        const { activeActions } = archInfo;
        // Widget
        const deletable =
            activeActions.delete &&
            (!groupByField || groupByField.type !== "many2many") &&
            !props.readonly;
        const editable = activeActions.edit && !props.readonly;
        this.dataState.widget = {
            deletable,
            editable,
        };
    }

    getRecordClasses() {
        const { archInfo, canResequence, forceGlobalClick, record, progressBarState } = this.props;
        const classes = ["o_kanban_record d-flex"];
        if (canResequence) {
            classes.push("o_draggable");
        }
        if (forceGlobalClick || archInfo.openAction || archInfo.canOpenRecords) {
            classes.push("cursor-pointer");
        }
        if (progressBarState) {
            const { fieldName, colors } = progressBarState.progressAttributes;
            const value = record.data[fieldName];
            const color = colors[value];
            classes.push(`oe_kanban_card_${color}`);
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(`o_kanban_color_${getColorIndex(value)}`);
        }
        if (!this.props.groupByField) {
            classes.push("flex-grow-1 flex-md-shrink-1 flex-shrink-0");
        }
        classes.push(archInfo.cardClassName);
        return classes.join(" ");
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev, newWindow) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        const { archInfo, forceGlobalClick, openRecord, record } = this.props;
        if (!forceGlobalClick && archInfo.openAction) {
            this.action.doActionButton(
                {
                    name: archInfo.openAction.action,
                    type: archInfo.openAction.type,
                    resModel: record.resModel,
                    resId: record.resId,
                    resIds: record.resIds,
                    context: record.context,
                    onClose: async () => {
                        await record.model.root.load();
                    },
                },
                {
                    newWindow,
                }
            );
        } else if (forceGlobalClick || this.props.archInfo.canOpenRecords) {
            openRecord(record, { newWindow });
        }
    }

    /**
     * @param {Object} params
     */
    triggerAction(params) {
        const { archInfo, openRecord, deleteRecord, record, archiveRecord } = this.props;
        const { type } = params;
        switch (type) {
            case "open": {
                return openRecord(record);
            }
            case "archive": {
                return archiveRecord(record, true);
            }
            case "unarchive": {
                return archiveRecord(record, false);
            }
            case "delete": {
                return deleteRecord(record);
            }
            case "set_cover": {
                const { autoOpen, fieldName } = params;
                const widgets = Object.values(archInfo.fieldNodes)
                    .filter((x) => x.name === fieldName)
                    .map((x) => x.widget);
                const field = record.fields[fieldName];
                if (
                    field.type === "many2one" &&
                    field.relation === "ir.attachment" &&
                    widgets.includes("attachment_image")
                ) {
                    this.dialog.add(KanbanCoverImageDialog, { autoOpen, fieldName, record });
                } else {
                    const warning = _t(
                        `Could not set the cover image: incorrect field ("%s") is provided in the view.`,
                        fieldName
                    );
                    this.notification.add({ title: warning, type: "danger" });
                }
                break;
            }
            default: {
                return this.notification.add(_t("Kanban: no action for type: %(type)s", { type }), {
                    type: "danger",
                });
            }
        }
    }

    /**
     * Returns the card template's rendering context.
     *
     * Note: the keys answer to outdated standards but should not be altered for
     * the sake of compatibility.
     *
     * @returns {Object}
     */
    get renderingContext() {
        const renderingContext = {
            context: this.props.record.context,
            JSON,
            luxon,
            record: this.dataState.record,
            selection_mode: this.props.forceGlobalClick,
            widget: this.dataState.widget,
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
        return renderingContext;
    }
}
