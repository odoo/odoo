// @ts-check

/** @module @web/views/view_utils - Shared utilities for view controllers (class names, active actions, archive, formatting) */

import { WarningDialog } from "@web/components/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/collections/objects";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { useService } from "@web/core/utils/hooks";
import { X2M_TYPES } from "@web/fields/field_types";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";

const NUMERIC_TYPES = ["integer", "float", "monetary"];

/**
 * @typedef ViewActiveActions
 * @property {"view"} type
 * @property {boolean} edit
 * @property {boolean} create
 * @property {boolean} delete
 * @property {boolean} duplicate
 */

/**
 * @param {string?} type
 * @returns {string | false}
 */
function getViewClass(type) {
    const isValidType = Boolean(type) && registry.category("views").contains(type);
    return isValidType && `o_${type}_view`;
}

/**
 * @param {string?} viewType
 * @param {Element?} rootNode
 * @param {string[]} additionalClassList
 * @returns {string}
 */
export function computeViewClassName(viewType, rootNode, additionalClassList = []) {
    const subType = rootNode?.getAttribute("js_class");
    const classList = rootNode?.getAttribute("class")?.split(" ") || [];
    const uniqueClasses = new Set([
        getViewClass(viewType),
        getViewClass(subType),
        ...classList,
        ...additionalClassList,
    ]);
    return Array.from(uniqueClasses)
        .filter((c) => c) // remove falsy values
        .join(" ");
}

/**
 * @param {any} record
 * @param {string} fieldName
 * @param {any} [fieldInfo]
 * @returns {string}
 */
export function getFormattedValue(record, fieldName, fieldInfo = null) {
    const field = record.fields[fieldName];
    /** @type {any} */
    const formatter = registry.category("formatters").get(field.type, (val) => val);
    const formatOptions = {};
    if (fieldInfo && formatter.extractOptions) {
        Object.assign(formatOptions, formatter.extractOptions(fieldInfo));
    }
    formatOptions.data = record.data;
    formatOptions.field = field;
    return record.data[fieldName] !== undefined
        ? formatter(record.data[fieldName], formatOptions)
        : "";
}

/**
 * @param {Element} rootNode
 * @returns {ViewActiveActions}
 */
export function getActiveActions(rootNode) {
    /** @type {ViewActiveActions} */
    const activeActions = {
        type: "view",
        edit: exprToBoolean(rootNode.getAttribute("edit"), true),
        create: exprToBoolean(rootNode.getAttribute("create"), true),
        delete: exprToBoolean(rootNode.getAttribute("delete"), true),
        duplicate: false,
    };
    activeActions.duplicate =
        activeActions.create && exprToBoolean(rootNode.getAttribute("duplicate"), true);
    return activeActions;
}

/**
 * @param {any} field
 * @returns {boolean}
 */
export function isX2Many(field) {
    return field && X2M_TYPES.includes(field.type);
}

/**
 * @param {Object} field
 * @returns {boolean} true iff the given field is a numeric field
 */
export function isNumeric(field) {
    return NUMERIC_TYPES.includes(field.type);
}

/**
 * @param {any} value
 * @returns {boolean}
 */
export function isNull(value) {
    return [null, undefined].includes(value);
}

/**
 * Transforms a string into a valid expression to be injected
 * in a template as a props via setAttribute.
 * Example: myString = `Some weird language quote (") `;
 *     should become in the template:
 *      <Component label="&quot;Some weird language quote (\\&quot;)&quot; " />
 *     which should be interpreted by owl as a JS expression being a string:
 *      `Some weird language quote (") `
 *
 * @param  {string} str The initial value: a pure string to be interpreted as such
 * @return {string}     the valid string to be injected into a component's node props.
 */
export function toStringExpression(str) {
    return `\`${str.replaceAll("`", "\\`")}\``;
}

// ---------------------------------------------------------------------------
// Controller utilities — shared logic extracted from form/list/kanban
// ---------------------------------------------------------------------------

/**
 * Compute the default model loading options for view controllers.
 *
 * A model loads lazily when it is not a controller reload, not inside a dialog,
 * and has a control panel — i.e. it is a top-level, first-paint view.
 * Embedded views (x2many) and dialog views must load eagerly so the
 * surrounding UI is never left with a visually empty nested component.
 *
 * @param {Object} env - OWL component environment
 * @param {Object} display - view display props (from standardViewProps)
 * @returns {{ lazy: boolean }}
 */
export function computeModelOptions(env, display) {
    return {
        lazy:
            !env.config.isReloadingController &&
            !env.inDialog &&
            !!display.controlPanel,
    };
}

/**
 * Initialize the four standard services every view controller needs.
 * Returns an object with { action, dialog, notification, orm } plus a
 * pre-built set of model UI hooks.
 *
 * @returns {{ action: Object, dialog: Object, notification: Object, orm: Object, uiHooks: Object }}
 */
export function useControllerServices() {
    const action = useService("action");
    const dialog = useService("dialog");
    const notification = useService("notification");
    const orm = useService("orm");
    const uiHooks = makeModelUIHooks({ action, dialog, notification });
    return { action, dialog, notification, orm, uiHooks };
}

/**
 * Determine if archive/unarchive actions should be available.
 *
 * Checks for the presence and writability of the `active` or `x_active`
 * field in the provided fields definition.
 *
 * @param {Object} fields - field definitions (props.fields or model.root.activeFields)
 * @returns {boolean}
 */
export function computeArchiveEnabled(fields) {
    if ("active" in fields) {
        return !fields.active.readonly;
    }
    if ("x_active" in fields) {
        return !fields.x_active.readonly;
    }
    return false;
}

/**
 * Build the final action menu items from static items and server-provided
 * action menus.
 *
 * This is the shared filter→sort→map pipeline that was duplicated in
 * form, list, and kanban controllers.
 *
 * @param {Object} staticItems - keyed by action name, each with
 *   { isAvailable?, sequence, icon, description, callback, ... }
 * @param {Object} [actionMenus] - server-provided { action: [], print: [] }
 * @returns {{ action: Object[], print: Object[] }}
 */
export function buildActionMenuItems(staticItems, actionMenus) {
    const staticActionItems = Object.entries(staticItems)
        .filter(([key, item]) => item.isAvailable === undefined || item.isAvailable())
        .sort(
            ([k1, item1], [k2, item2]) => (item1.sequence || 0) - (item2.sequence || 0),
        )
        .map(([key, item]) =>
            Object.assign(
                { key, groupNumber: STATIC_ACTIONS_GROUP_NUMBER },
                omit(item, "isAvailable", "sequence"),
            ),
        );

    return {
        action: [...staticActionItems, ...(actionMenus?.action || [])],
        print: actionMenus?.print,
    };
}

/**
 * Build default UI hook implementations from controller services.
 *
 * Controllers spread these into their model hooks so that the data layer
 * (RelationalModel / Record / DynamicList) never imports or calls UI
 * services directly.
 *
 * @param {{ action: Object, dialog: Object, notification: Object }} services
 * @returns {Object} hook implementations keyed by hook name
 */
export function makeModelUIHooks({ action, dialog, notification }) {
    return {
        onDisplayOnchangeWarning(warning) {
            const { type, title, message, className, sticky } = warning;
            if (type === "dialog") {
                dialog.add(WarningDialog, { title, message });
            } else {
                notification.add(message, {
                    className,
                    sticky,
                    title,
                    type: "warning",
                });
            }
        },
        onDisplayInvalidFields() {
            return notification.add(_t("Missing required fields"), {
                type: "danger",
            });
        },
        onDisplayUrgentSave(message) {
            return notification.add(message, { sticky: true });
        },
        onDisplayPropertyWarning(message) {
            notification.add(message, { type: "warning" });
        },
        onDisplayArchiveAction(actionResult, reload) {
            if (actionResult && Object.keys(actionResult).length) {
                return action.doAction(actionResult, { onClose: reload });
            } else {
                return reload();
            }
        },
        onConfirmArchive(isSelected, archiveFn, unarchiveFn, dialogProps = {}) {
            const defaultProps = {
                body: _t(
                    "Are you sure that you want to archive all the selected records?",
                ),
                cancel: () => {},
                confirm: () => {
                    archiveFn();
                },
                confirmLabel: _t("Archive"),
            };
            dialog.add(ConfirmationDialog, { ...defaultProps, ...dialogProps });
        },
        onConfirmDuplicate(resIds, copyFn) {
            if (resIds.length > 1) {
                dialog.add(ConfirmationDialog, {
                    body: _t(
                        "Are you sure that you want to duplicate all the selected records?",
                    ),
                    confirm: async () => copyFn(resIds),
                    cancel: () => {},
                    confirmLabel: _t("Confirm"),
                });
            } else {
                return copyFn(resIds);
            }
        },
        onDisplayLimitNotification(msg) {
            notification.add(msg);
        },
    };
}

// Register shared utilities for lower layers via registry indirection
registry
    .category("shared_components")
    .add("computeViewClassName", computeViewClassName);
