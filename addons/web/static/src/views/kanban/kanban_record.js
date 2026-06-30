import { browser } from "@web/core/browser/browser";
import { props, t } from "@odoo/owl";
import { ColorList } from "@web/core/colorlist/colorlist";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useRef } from "@web/owl2/utils";
import {
    CardRenderer,
    getFormattedRecord,
    getImageSrcFromRecordInfo,
    getRawValue,
} from "@web/views/card/card_renderer";
import { TOUCH_SELECTION_THRESHOLD } from "@web/views/utils";
import { KanbanCoverImageDialog } from "./kanban_cover_image_dialog";
import { KanbanDropdownMenuWrapper } from "./kanban_dropdown_menu_wrapper";

export { getFormattedRecord, getImageSrcFromRecordInfo, getRawValue };

// These classes determine whether a click on a record should open it.
export const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action", "[data-bs-toggle]"].join(
    ","
);
export const MENU_ATTRIBUTE = "menu";

const { COLORS } = ColorList;

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

export const kanbanRecordProps = {
    archInfo: t.any(),
    archiveRecord: t.function().optional(() => () => {}),
    canOpenRecords: t.any().optional(),
    canResequence: t.any().optional(),
    cardColorField: t.any().optional(),
    colors: t.any().optional(COLORS),
    Compiler: t.any().optional(),
    deleteRecord: t.function().optional(() => () => {}),
    forceGlobalClick: t.any().optional(),
    getSelection: t.function().optional(() => () => []),
    groupByField: t.any().optional(),
    openAction: t.any().optional(),
    openRecord: t.function().optional(() => () => {}),
    progressBarState: t.any().optional(),
    readonly: t.any().optional(),
    record: t.any(),
    selectionAvailable: t.any().optional(false),
    toggleSelection: t.function().optional(() => () => {}),
};

export class KanbanRecord extends CardRenderer {
    static template = "web.KanbanRecord";
    static menuTemplate = "web.KanbanMenu";
    static components = {
        ...CardRenderer.components,
        Dropdown,
        DropdownItem,
        KanbanDropdownMenuWrapper,
        KanbanCoverImageDialog,
    };
    props = props(kanbanRecordProps);

    static MENU_ATTRIBUTE = MENU_ATTRIBUTE;
    static CANCEL_GLOBAL_CLICK = CANCEL_GLOBAL_CLICK;
    static PROGRESS_COLOR_PREFIX = "oe_kanban_card_";
    static HIGHLIGHT_COLOR_PREFIX = "o_kanban_color_";
    static CoverImageDialog = KanbanCoverImageDialog;

    setup() {
        super.setup();

        this.LONG_TOUCH_THRESHOLD = this.props.canResequence ? 600 : TOUCH_SELECTION_THRESHOLD;
        this.longTouchTimer = null;
        this.touchStartMs = 0;
        this.showMenu = this.constructor.MENU_ATTRIBUTE in this.templates;

        this.rootRef = useRef("root");
    }

    get renderingContext() {
        return {
            ...super.renderingContext,
            selection_mode: this.props.forceGlobalClick,
        };
    }

    async archiveRecord(record, active) {
        if (active) {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Are you sure that you want to archive this record?"),
                confirmLabel: _t("Archive"),
                confirm: () => record.archive(),
                cancel: () => {},
            });
        } else {
            return record.unarchive();
        }
    }

    createWidget(props) {
        super.createWidget(props);
        if (this.props.groupByField?.type === "many2many") {
            this.dataState.widget.deletable = false;
        }
    }

    getCardClasses() {
        const classes = super.getCardClasses().split(" ");

        classes.push("o_kanban_record");

        const {
            canOpenRecords,
            canResequence,
            cardColorField,
            forceGlobalClick,
            openAction,
            record,
            progressBarState,
        } = this.props;
        if (canResequence) {
            classes.push("o_draggable");
        }
        if (forceGlobalClick || openAction || canOpenRecords) {
            classes.push("cursor-pointer");
        }
        if (progressBarState) {
            const { fieldName, colors } = progressBarState.progressAttributes;
            const value = record.data[fieldName];
            const color = colors[value];
            if (color) {
                classes.push(`${this.constructor.PROGRESS_COLOR_PREFIX}${color}`);
            }
        }
        if (cardColorField) {
            const value = record.data[cardColorField];
            classes.push(`${this.constructor.HIGHLIGHT_COLOR_PREFIX}${getColorIndex(value)}`);
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
        if (
            this.offlinePlugin.isOffline() &&
            !this.props.record.model.useSampleModel &&
            !this.offlinePlugin.isAvailableOffline(this.env.config.actionId, "form", record.resId)
        ) {
            classes.push("o_disabled_offline");
        }
        return classes.join(" ");
    }

    /**
     * @param {Object} params
     */
    triggerAction(params) {
        const { archInfo, deleteRecord, openRecord, record } = this.props;
        const { type } = params;
        switch (type) {
            case "open": {
                return openRecord(record);
            }
            case "archive": {
                return this.archiveRecord(record, true);
            }
            case "unarchive": {
                return this.archiveRecord(record, false);
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
                    this.dialog.add(this.constructor.CoverImageDialog, {
                        autoOpen,
                        fieldName,
                        record,
                    });
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
                return this.notification.add(_t("Card: no action for type: %(type)s", { type }), {
                    type: "danger",
                });
            }
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev, newWindow) {
        if (ev.target.closest(this.constructor.CANCEL_GLOBAL_CLICK)) {
            return;
        }
        if (this.props.getSelection().length > 0 || ev.altKey) {
            ev.stopPropagation();
            ev.preventDefault();
            this.rootRef.el.focus();
            this.props.toggleSelection(this.props.record, ev.shiftKey);
            return;
        }
        const { forceGlobalClick, canOpenRecords, openAction, openRecord, record } = this.props;
        if (!forceGlobalClick && openAction) {
            this.action.doActionButton(
                {
                    name: openAction.action,
                    type: openAction.type,
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
        } else if (forceGlobalClick || canOpenRecords) {
            openRecord(record, { newWindow });
        }
    }

    resetLongTouchTimer() {
        if (this.longTouchTimer) {
            browser.clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    }

    onTouchStart() {
        this.touchStartMs = Date.now();
        if (this.longTouchTimer === null) {
            this.longTouchTimer = browser.setTimeout(() => {
                this.props.record.toggleSelection(true);
                this.resetLongTouchTimer();
            }, this.LONG_TOUCH_THRESHOLD);
        }
    }

    onTouchEnd() {
        const elapsedTime = Date.now() - this.touchStartMs;
        if (elapsedTime < this.LONG_TOUCH_THRESHOLD) {
            this.resetLongTouchTimer();
        }
    }

    onTouchMoveOrCancel() {
        this.resetLongTouchTimer();
    }
}
