// @ts-check
/** @odoo-module native */
import { Component, onWillStart, onWillUpdateProps, useRef } from "@odoo/owl";
import { ColorList } from "@web/components/colorlist/colorlist";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useAction } from "@web/core/action_port";
import { hasTouch } from "@web/core/browser/feature_detection";
import { getColorIndex } from "@web/core/colors/colors";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { luxon } from "@web/core/l10n/luxon";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { useRenderCounter } from "@web/core/utils/render_instrumentation";
import { imageUrl } from "@web/core/utils/urls";
import { Field } from "@web/fields/field";
import { fileTypeMagicWordMap } from "@web/fields/media/image/image_field";
import { useLongTouchSelection } from "@web/views/multi_record_selection";
import { SELF_HANDLED_SELECTOR } from "@web/views/self_handled";
import { ViewButton } from "@web/views/view_button/view_button";
import { compileViewTemplates } from "@web/views/view_compiler";
import { getFormattedValue, getOpenActionParams } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

import { KANBAN_CARD_ATTRIBUTE, KANBAN_MENU_ATTRIBUTE } from "./kanban_arch_parser.js";
import { KanbanCompiler } from "./kanban_compiler.js";
import { KanbanCoverImageDialog } from "./kanban_cover_image_dialog.js";
import { KanbanDropdownMenuWrapper } from "./kanban_dropdown_menu_wrapper.js";

const { COLORS } = ColorList;

const formatters = registry.category("formatters");

export const CANCEL_GLOBAL_CLICK = [
    "a",
    ".dropdown",
    ".oe_kanban_action",
    SELF_HANDLED_SELECTOR,
].join(",");

/**
 * @param {any} record
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
            return value?.id || false;
        }
        case "date":
        case "datetime": {
            return typeof value?.toISO === "function" ? value.toISO() : value;
        }
        default: {
            return value;
        }
    }
}

/**
 * @param {any} record
 * @param {string} fieldName
 * @returns {string}
 */
function getValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    const formatter = formatters.get(field.type, String);
    return formatter(value, { field, data: record.data });
}

/**
 * @param {any} record
 * @returns {any}
 */
export function getFormattedRecord(record) {
    const entries = Object.create(null);
    /** @type {Set<string> | null} */
    let fieldNameSet = null;
    let memoKey = null;
    const getFieldNames = () => {
        const key = record.activeFields;
        if (fieldNameSet === null || memoKey !== key) {
            memoKey = key;
            fieldNameSet = new Set(record.fieldNames);
        }
        return fieldNameSet;
    };
    const getEntry = (fieldName) => {
        if (!entries[fieldName]) {
            if (fieldName === "id") {
                entries[fieldName] = {
                    get value() {
                        return record.resId;
                    },
                    get raw_value() {
                        return record.resId;
                    },
                };
            } else {
                entries[fieldName] = {
                    get value() {
                        return getValue(record, fieldName);
                    },
                    get raw_value() {
                        return getRawValue(record, fieldName);
                    },
                };
            }
        }
        return entries[fieldName];
    };
    const isField = (p) =>
        typeof p === "string" && (p === "id" || getFieldNames().has(p));
    return new Proxy(Object.create(Object.prototype), {
        get(target, p) {
            return isField(p) ? getEntry(p) : Reflect.get(target, p);
        },
        has(target, p) {
            return isField(p) || Reflect.has(target, p);
        },
        ownKeys(target) {
            return [...new Set(["id", ...getFieldNames(), ...Reflect.ownKeys(target)])];
        },
        getOwnPropertyDescriptor(target, p) {
            if (isField(p)) {
                return { enumerable: true, configurable: true, value: getEntry(p) };
            }
            return Reflect.getOwnPropertyDescriptor(target, p);
        },
    });
}

/**
 * @param {any} record
 * @param {string} [model]
 * @param {string} [field]
 * @param {number | [number, ...any[]]} [idOrIds]
 * @param {string} [placeholder]
 * @returns {string}
 */
export function getImageSrcFromRecordInfo(record, model, field, idOrIds, placeholder) {
    const id = (Array.isArray(idOrIds) ? idOrIds[0] : idOrIds) || null;
    const isCurrentRecord =
        record.resModel === model && (record.resId === id || (!record.resId && !id));
    const fieldVal = record.data[field];
    if (isCurrentRecord && fieldVal && !isBinSize(fieldVal)) {
        const type = fileTypeMagicWordMap[fieldVal[0] ?? ""];
        return `data:image/${type};base64,${fieldVal}`;
    } else if (placeholder && (!model || !field || !id || !fieldVal)) {
        return placeholder;
    } else {
        const unique = isCurrentRecord && record.data.write_date;
        return imageUrl(/** @type {string} */ (model), id, field, { unique });
    }
}

function isBinSize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

const log = makeLogger("web.view.kanban.record");

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
        getSelection: () => [],
        archiveRecord: () => {},
        openRecord: () => {},
        selectionAvailable: false,
        toggleSelection: () => {},
    };
    static props = [
        "archInfo",
        "canResequence?",
        "colors?",
        "Compiler?",
        "forceGlobalClick?",
        "getSelection?",
        "group?",
        "groupByField?",
        "deleteRecord?",
        "archiveRecord?",
        "openRecord?",
        "readonly?",
        "record",
        "selectionAvailable?",
        "progressBarState?",
        "toggleSelection?",
    ];
    static KANBAN_CARD_ATTRIBUTE = KANBAN_CARD_ATTRIBUTE;
    static KANBAN_MENU_ATTRIBUTE = KANBAN_MENU_ATTRIBUTE;
    static menuTemplate = "web.KanbanRecordMenu";
    static template = "web.KanbanRecord";

    /** @returns {number} a draggable card waits longer before a long touch selects it */
    get LONG_TOUCH_THRESHOLD() {
        return this.props.canResequence ? 600 : 400;
    }

    setup() {
        useLifecycleLog(log);
        useRenderCounter("kanban.KanbanRecord");
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.action = useAction();
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        const { Compiler, archInfo } = this.props;
        const ViewCompiler = Compiler || KanbanCompiler;
        const { templateDocs: templates } = archInfo;

        this.templates = compileViewTemplates(ViewCompiler, templates);

        this.showMenu =
            /** @type {any} */ (this.constructor).KANBAN_MENU_ATTRIBUTE in templates;

        this.createWidget(this.props);
        this.formattedRecord = getFormattedRecord(this.props.record);
        onWillUpdateProps((nextProps) => {
            this.createWidget(nextProps);
            if (nextProps.record !== this.props.record) {
                this.formattedRecord = getFormattedRecord(nextProps.record);
            }
        });
        // a microtask boundary before the first render: a card created by a
        // render fiber that a concurrent state write supersedes would otherwise
        // render on the discarded fiber (pinned by "rerenders only once after
        // resequencing records")
        onWillStart(() => Promise.resolve());
        this.rootRef = useRef("root");
        this.hasTouch = hasTouch();

        this.longTouch = useLongTouchSelection({
            getLongTouchThreshold: () =>
                /** @type {number} */ (this.LONG_TOUCH_THRESHOLD),
            onLongTouch: () => this.props.record.toggleSelection(true),
        });
    }

    get record() {
        return this.formattedRecord;
    }

    getFormattedValue(fieldId) {
        const { archInfo, record } = this.props;
        const { name } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, archInfo.fieldNodes[fieldId]);
    }

    /** @param {Object} props */
    createWidget(props) {
        const { archInfo, groupByField } = props;
        const { activeActions } = archInfo;
        const deletable =
            activeActions.delete &&
            (!groupByField || groupByField.type !== "many2many") &&
            !props.readonly;
        const editable = activeActions.edit && !props.readonly;
        this.widget = {
            deletable,
            editable,
        };
    }

    getRecordClasses() {
        const { archInfo, canResequence, forceGlobalClick, record, progressBarState } =
            this.props;
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
            if (color) {
                classes.push(`oe_kanban_card_${color}`);
            }
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(`o_kanban_color_${getColorIndex(value)}`);
        }
        if (!this.props.groupByField) {
            classes.push("flex-grow-1 flex-md-shrink-1 flex-shrink-0");
        }
        if (this.props.selectionAvailable) {
            classes.push("o_record_selection_available");
        }
        if (this.props.record.selected) {
            classes.push("o_record_selected");
        }
        classes.push(archInfo.cardClassName);
        return classes.join(" ");
    }

    /** @param {MouseEvent} ev */
    onGlobalClick(ev, newWindow) {
        if (/** @type {HTMLElement} */ (ev.target).closest(CANCEL_GLOBAL_CLICK)) {
            return;
        }
        if (this.props.getSelection().length > 0 || ev.altKey) {
            ev.stopPropagation();
            ev.preventDefault();
            this.rootRef.el?.focus();
            this.props.toggleSelection(this.props.record, ev.shiftKey);
            return;
        }
        const { archInfo, forceGlobalClick, openRecord, record } = this.props;
        if (!forceGlobalClick && archInfo.openAction) {
            this.action.doActionButton(
                getOpenActionParams(archInfo.openAction, record),
                { newWindow },
            );
        } else if (forceGlobalClick || this.props.archInfo.canOpenRecords) {
            openRecord(record, { newWindow });
        }
    }

    resetLongTouchTimer() {
        this.longTouch.resetLongTouchTimer();
    }

    onTouchStart() {
        this.longTouch.onTouchStart();
    }
    onTouchEnd() {
        this.longTouch.onTouchEnd();
    }
    onTouchMoveOrCancel() {
        this.longTouch.onTouchMove();
    }

    /** @param {Object} params */
    triggerAction(params) {
        const { archInfo, openRecord, deleteRecord, record, archiveRecord } =
            this.props;
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
                const { fieldName } = params;
                const widgets = Object.values(archInfo.fieldNodes)
                    .filter((x) => x.name === fieldName)
                    .map((x) => x.widget);
                const field = record.fields[fieldName];
                if (
                    field.type === "many2one" &&
                    field.relation === "ir.attachment" &&
                    widgets.includes("attachment_image")
                ) {
                    this.dialog.add(KanbanCoverImageDialog, {
                        fieldName,
                        record,
                    });
                } else {
                    const warning = _t(
                        `Could not set the cover image: incorrect field ("%s") is provided in the view.`,
                        fieldName,
                    );
                    this.notification.add(warning, { type: "danger" });
                }
                break;
            }
            default: {
                return this.notification.add(
                    _t("Kanban: no action for type: %(type)s", { type }),
                    {
                        type: "danger",
                    },
                );
            }
        }
    }

    /** @returns {Object} */
    get renderingContext() {
        const renderingContext = {
            context: this.props.record.context,
            JSON,
            luxon,
            record: this.formattedRecord,
            selection_mode: this.props.forceGlobalClick,
            widget: this.widget,
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
        return renderingContext;
    }
}
