import { proxy, signal, t, useListener, usePlugin, useProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { ORM } from "@web/core/orm_plugin";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useBus, useService } from '@web/core/utils/hooks';
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export const ExpenseDocumentDropZone = (T, parentProps) => class ExpenseDocumentDropZone extends T {
    props = useProps({
        ...parentProps,
        uploadDocument: t.function(),
    });

    setup() {
        super.setup();
        this.dragState = proxy({
            showDragZone: false,
        });

        // The drop zone is the whole content area the renderer is displayed in.
        const contentEl = () => this.rootRef()?.closest(".o_content");
        useListener(contentEl, "dragover", this.highlight.bind(this));
        useListener(contentEl, "dragleave", this.unhighlight.bind(this));
        useListener(contentEl, "drop", this.onDrop.bind(this));

        useListener(this.rootRef, 'click', (ev) => {
            let targetElement = ev.target;
            if (targetElement.closest('.o_view_nocontent_expense_receipt')) {
                this.props.uploadDocument();
            }
        });
    }

    highlight(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.dragState.showDragZone = true;
    }

    unhighlight(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.dragState.showDragZone = false;
    }

    async onDrop(ev) {
        ev.preventDefault();
        await this.env.bus.trigger("change_file_input", {
            files: ev.dataTransfer.files,
        });
        this.dragState.showDragZone = false;
    }
};

/**
 * Turns uploaded files into expenses, and opens the expenses it created.
 *
 * @param {object} [params]
 * @param {() => string} [params.modelName] model the attachments are turned into
 * @param {() => string} [params.viewType] view type `create_expense_from_attachments` generates for
 * @param {() => object} [params.context]
 */
export function useExpenseDocumentUpload({ modelName, viewType, context } = {}) {
    const actionPlugin = usePlugin(ActionPlugin);
    const notification = usePlugin(NotificationPlugin);
    const orm = usePlugin(ORM);
    const ui = usePlugin(UIPlugin);
    const http = useService("http");

    modelName ||= () => "hr.expense";
    viewType ||= () => (ui.isSmall() ? "kanban" : "list");
    context ||= () => ({});

    let createdExpenseIds = [];

    async function generateOpenExpensesAction(currentAction) {
        const actionName = _t("Generate Expenses");
        let domain = [['id', 'in', createdExpenseIds]];
        let options = {};
        if (currentAction && currentAction.name === actionName) {
            domain = Domain.or([domain, currentAction.domain]).toList();
            options['stackPosition'] = 'replaceCurrentAction';
        }
        const views = ui.isSmall()
            ? [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ]
            : [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ];
        await actionPlugin.doAction({
            'name': actionName,
            'res_model': modelName(),
            'type': 'ir.actions.act_window',
            'views': views,
            'domain': domain,
            'context': context(),
        }, options);
    }

    async function uploadFiles(files) {
        const params = {
            csrf_token: odoo.csrf_token,
            ufile : [...files],
            model: modelName(),
            id: 0,
        };

        const attachments = await http.post('/web/binary/upload_attachment', params);
        if (attachments.error) {
            throw new Error(attachments.error);
        }

        const attachmentIds = attachments.map((a) => a.id);
        if (!attachmentIds.length) {
            notification.add(
                _t('An error occurred during the upload')
            );
            return;
        }

        const newExpenseIds = await orm.call(
            modelName(),
            'create_expense_from_attachments',
            [attachmentIds, viewType()],
            { context: context() },
        );
        createdExpenseIds = [...createdExpenseIds, ...newExpenseIds];
    }

    return { generateOpenExpensesAction, uploadFiles };
}

/**
 * `useExpenseDocumentUpload` driven by a hidden `<input type="file">`, for the
 * views that offer an Upload button and a drop zone.
 *
 * @param {object} params
 * @param {import("@odoo/owl").EventBus} params.bus bus the drop zone reports dropped files on
 * @see useExpenseDocumentUpload for the other parameters
 */
export function useExpenseDocumentUploadInput({ bus, ...params } = {}) {
    const upload = useExpenseDocumentUpload(params);
    const actionPlugin = usePlugin(ActionPlugin);
    const fileInput = signal.ref();
    let uploadsProcessing = 0;

    async function onChangeFileInput() {
        try {
            await upload.uploadFiles([...fileInput().files]);
            if (uploadsProcessing === 1) {
                await upload.generateOpenExpensesAction(actionPlugin.currentController.action);
            }
        } finally {
            uploadsProcessing--;
        }
    }

    function uploadDocument() {
        uploadsProcessing++;
        fileInput().click();
    }

    useBus(bus, "change_file_input", async (ev) => {
        fileInput().files = ev.detail.files;
        uploadsProcessing++;
        await onChangeFileInput();
    });

    return { ...upload, fileInput, onChangeFileInput, uploadDocument };
}
