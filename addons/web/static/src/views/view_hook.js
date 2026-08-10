import { onWillUnmount, useListener, usePlugin } from "@odoo/owl";
import {
    ConfirmationDialog,
    deleteConfirmationMessage,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { rpc } from "@web/core/network/rpc";
import { ORM } from "@web/core/orm_plugin";
import { evaluateExpr } from "@web/core/py_js/py";
import { useBus, useService } from "@web/core/utils/hooks";
import { DynamicList } from "@web/model/relational_model/dynamic_list";
import { useEnv } from "@web/owl2/utils";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";

/**
 * Allows for a component (usually a View component) to handle links with
 * attribute type="action". This is used to support onboarding banners and content helpers.
 *
 * A `keepLast` property must be present in the owl environment to allow coordinating
 * between clicks. @see @web/core/utils/concurrency:KeepLast
 *
 * Note that this is similar but quite different from action buttons, since action links
 * are not dynamic according to the record.
 *
 * @param {string} resModel default resModel to which actions will apply
 * @param {() => any} reload function to run to reload, if a button has data-reload-on-close
 */
export function useActionLinks(resModel, reload) {
    const { doAction } = useService("action");
    const { keepLast } = useEnv();
    const orm = usePlugin(ORM);

    async function handler(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        let target = ev.target;
        if (target.tagName !== "A") {
            target = target.closest("a");
        }
        const data = target.dataset;

        if (data.method !== undefined && data.model !== undefined) {
            const options = {};
            if (data.reloadOnClose) {
                options.onClose = reload;
            }
            const action = await keepLast.add(orm.call(data.model, data.method));
            if (action !== null) {
                keepLast.add(Promise.resolve(doAction(action, options)));
            }
        } else if (target.getAttribute("name")) {
            const options = {};
            if (data.context) {
                options.additionalContext = evaluateExpr(data.context);
            }
            keepLast.add(doAction(target.getAttribute("name"), options));
        } else {
            let views;
            const resId = data.resid ? parseInt(data.resid, 10) : null;
            if (data.views) {
                views = evaluateExpr(data.views);
            } else {
                views = resId
                    ? [[false, "form"]]
                    : [
                          [false, "list"],
                          [false, "form"],
                      ];
            }
            const action = {
                name: target.getAttribute("title") || target.textContent.trim(),
                type: "ir.actions.act_window",
                res_model: data.model || resModel,
                target: "current",
                views,
                domain: data.domain ? evaluateExpr(data.domain) : [],
            };
            if (resId) {
                action.res_id = resId;
            }

            const options = {};
            if (data.context) {
                options.additionalContext = evaluateExpr(data.context);
            }
            keepLast.add(doAction(action, options));
        }
    }

    return (ev) => {
        const a = ev.target.closest(`a[type="action"]`);
        if (a && ev.currentTarget.contains(a)) {
            handler(ev);
        }
    };
}

export function useBounceButton(containerRef, shouldBounce) {
    let timeout;
    const ui = useService("ui");
    const onClick = (ev) => {
        const button = ui.activeElement.querySelector("[data-bounce-button]");
        if (button && shouldBounce(ev.target)) {
            button.classList.add("o_catch_attention");
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                button.classList.remove("o_catch_attention");
            }, 400);
        }
    };
    useListener(containerRef, "click", onClick);
    onWillUnmount(() => clearTimeout(timeout));
}

export function useExportRecords(env, context, getDefaultExportList) {
    const { model, searchModel } = env;
    useBus(searchModel, "direct-export-data", async () => {
        _downloadExport(getDefaultExportList(), false, "xlsx");
    });
    const _getExportedFields = async (isCompatible, parentParams) => {
        const root = model.root;
        let domain = parentParams ? [] : root.domain;
        if (!root.isDomainSelected && root.selection.length > 0) {
            const ids = root.selection.map((e) => e.resId);
            domain = [["id", "in", ids]];
        }
        return await rpc("/web/export/get_fields", {
            model: root.resModel,
            domain,
            import_compat: isCompatible,
            ...parentParams,
        });
    };

    const _downloadExport = async (fields, import_compat, format) => {
        const root = model.root;
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type || field.type,
        }));
        if (import_compat) {
            exportedFields.unshift({
                name: "id",
                label: _t("External ID"),
            });
        }
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: root.context,
                    domain: root.domain,
                    fields: exportedFields,
                    groupby: root.groupBy,
                    ids:
                        !root.isDomainSelected && root.selection.length > 0
                            ? root.selection.map((e) => e.resId)
                            : false,
                    model: root.resModel,
                }),
            },
            url: `/web/export/${format}`,
        });
    };

    return () => {
        const root = model.root;
        model.dialog.add(ExportDataDialog, {
            context: root.context,
            defaultExportList: getDefaultExportList(),
            download: _downloadExport,
            getExportedFields: _getExportedFields,
            root,
        });
    };
}

export function useDeleteRecords(model) {
    function getDefaultDialogProps(records) {
        const isDynamicList = model.root instanceof DynamicList;
        let body = deleteConfirmationMessage;
        if (
            records?.length > 1 ||
            (isDynamicList && (model.root.isDomainSelected || model.root.selection.length > 1))
        ) {
            body = _t("Are you sure you want to delete these records?");
        }
        let confirm = () => records.forEach((r) => r.delete());
        if (isDynamicList) {
            confirm = () => model.root.deleteRecords(records);
        }
        return {
            body,
            cancel: () => {},
            cancelLabel: _t("No, keep it"),
            confirm,
            confirmLabel: _t("Delete"),
            confirmClass: "btn-danger",
            title: _t("Bye-bye, record!"),
        };
    }
    return (dialogProps, records) => {
        const defaultProps = getDefaultDialogProps(records);
        model.dialog.add(ConfirmationDialog, { ...defaultProps, ...dialogProps });
    };
}
