import { _t } from "@web/core/l10n/translation";
import { ColorList } from "@web/core/colorlist/colorlist";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
import { Field } from "@web/views/fields/field";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { getFormattedValue } from "../utils";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanCoverImageDialog } from "./kanban_cover_image_dialog";
import { KanbanRecordMenu } from "./kanban_record_menu";

import { Component, xml } from "@odoo/owl";
const { COLORS } = ColorList;

/**
 * Returns the class name of a record according to its color.
 */
function getColorClass(value) {
    return `o_kanban_color_${getColorIndex(value)}`;
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

export class KanbanRecord extends Component {
    static template = xml`<t t-call="{{ template }}" t-call-context="this.renderingContext"/>`;
    static components = {
        KanbanRecordMenu,
        Field,
        ViewButton,
        Widget,
    };
    static defaultProps = {
        colors: COLORS, // legacy
        deleteRecord: () => {},
        archiveRecord: () => {},
        openRecord: () => {},
    };
    static props = [
        "archInfo",
        "canResequence?",
        "Compiler?",
        "forceGlobalClick?",
        "group?", // to check
        "list",
        "deleteRecord?",
        "archiveRecord?",
        "openRecord?",
        "readonly?",
        "record",
        "progressBarState?",
        "colors?", // legacy
        "templates?", // legacy
    ];
    static Compiler = KanbanCompiler;

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;

        this.dialog = useService("dialog");
        this.notification = useService("notification");

        const ViewCompiler = this.props.Compiler || this.constructor.Compiler;
        const templates = useViewCompiler(ViewCompiler, { kanban: this.props.archInfo.xmlDoc });
        this.template = templates.kanban;
    }

    get canDelete() {
        const { archInfo, list } = this.props;
        return (
            archInfo.activeActions.delete &&
            (!list.groupByField || list.groupByField.type !== "many2many")
        );
    }

    get canEdit() {
        return this.props.archInfo.activeActions.edit;
    }

    get rootClass() {
        const { archInfo, canResequence, forceGlobalClick, record, progressBarState } = this.props;
        const classes = ["o_kanban_record"];
        if (archInfo.cardClassName) {
            classes.push(archInfo.cardClassName);
        }
        if (canResequence) {
            classes.push("o_draggable");
        }
        if (forceGlobalClick || archInfo.openAction || archInfo.allowGlobalClick) {
            classes.push("o_kanban_global_click");
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
            classes.push(getColorClass(value));
        }
        return classes.join(" ");
    }

    getFormattedValue(fieldId) {
        const { archInfo, record } = this.props;
        const { attrs, name } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, attrs);
    }

    /**
     * @param {Object} params
     */
    triggerAction(type, ev) {
        const { archInfo, openRecord, deleteRecord, record, archiveRecord } = this.props;
        switch (type) {
            case "edit": {
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
                const fieldName = ev.target.getAttribute("data-field");
                const widgets = Object.values(archInfo.fieldNodes)
                    .filter((x) => x.name === fieldName)
                    .map((x) => x.widget);
                const field = record.fields[fieldName];
                if (
                    field &&
                    field.type === "many2one" &&
                    field.relation === "ir.attachment" &&
                    widgets.includes("attachment_image")
                ) {
                    this.dialog.add(KanbanCoverImageDialog, { fieldName, record });
                } else {
                    const message = _t(
                        `Could not set the cover image: incorrect field ("%s") is provided in the view.`,
                        fieldName
                    );
                    this.notification.add(message, { type: "danger" });
                }
                break;
            }
            default: {
                return this.notification.add(_t("Kanban: no action for type: %s", type), {
                    type: "danger",
                });
            }
        }
    }

    /**
     * @returns {Object}
     */
    get renderingContext() {
        return {
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
    }
}
