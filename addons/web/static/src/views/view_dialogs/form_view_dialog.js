import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";
import { View } from "@web/views/view";

import { Component, props, t } from "@odoo/owl";

export const formViewDialogProps = {
    close: t.function(),
    resModel: t.string(),

    context: t.object().optional(),
    expandedFormRef: t.string().optional(),
    nextRecordsContext: t.object().optional(),
    readonly: t.boolean().optional(),
    onRecordSaved: t.function().optional(() => () => {}),
    onRecordSave: t.function().optional(),
    onRecordDiscarded: t.function().optional(),
    removeRecord: t.function().optional(),
    resId: t.or([t.number(), t.boolean()]).optional(),
    title: t.string().optional(),
    viewId: t.or([t.number(), t.boolean()]).optional(),
    preventCreate: t.boolean().optional(false),
    preventEdit: t.boolean().optional(false),
    canExpand: t.boolean().optional(true),
    isToMany: t.boolean().optional(false),
    // from Dialog.props.size
    size: t.selection(["sm", "md", "lg", "xl", "fs", "fullscreen"]).optional(),
};

export class FormViewDialog extends Component {
    static template = "web.FormViewDialog";
    static components = { Dialog, View };
    props = props(formViewDialogProps);

    setup() {
        super.setup();

        this.actionService = useService("action");
        this.modalRef = useChildRef();
        this.env.dialogData.dismiss = () => this.discardRecord();

        const buttonDialogTemplate = this.props.isToMany
            ? "web.FormViewDialog.ToMany.buttons"
            : "web.FormViewDialog.ToOne.buttons";

        this.currentResId = this.props.resId;

        if (this.props.canExpand) {
            this.onExpandCallback = this.onExpand.bind(this);
        }

        this.viewProps = {
            type: "form",
            buttonDialogTemplate,

            context: this.props.context || {},
            display: { controlPanel: false },
            readonly: this.props.readonly,
            resId: this.props.resId || false,
            resModel: this.props.resModel,
            viewId: this.props.viewId || false,
            preventCreate: this.props.preventCreate,
            preventEdit: this.props.preventEdit,
            discardRecord: this.discardRecord.bind(this),
            saveRecord: async (record, params) => {
                let saved;
                if (this.props.onRecordSave) {
                    saved = await this.props.onRecordSave(record);
                } else {
                    saved = await record.save({ reload: false });
                    if (saved) {
                        this.currentResId = record.resId;
                        await this.props.onRecordSaved(record);
                    }
                }
                if (saved) {
                    await this.onRecordSaved(record, params);
                }
                return saved;
            },

            __beforeLeave__: new CallbackRecorder(),
        };
        if (this.props.removeRecord) {
            this.viewProps.removeRecord = async () => {
                await this.props.removeRecord();
                this.props.close();
            };
        }
    }

    /**
     * overridable method defining what to do on save
     * @param {*} record, record that was saved
     * @param {*} params, additional parameters passed to "save"
     */
    async onRecordSaved(record, params) {
        if (params?.saveAndNew) {
            this.currentResId = false;
            const context = this.props.nextRecordsContext || this.props.context || {};
            await record.model.load({ resId: false, context });
        } else {
            this.props.close();
        }
    }

    async discardRecord() {
        if (this.props.onRecordDiscarded) {
            await this.props.onRecordDiscarded();
        }
        this.props.close();
    }

    async onExpand() {
        const beforeLeaveCallbacks = this.viewProps.__beforeLeave__.callbacks;
        const res = await Promise.all(beforeLeaveCallbacks.map((callback) => callback()));
        if (!res.includes(false)) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: this.props.resModel,
                res_id: this.currentResId,
                views: [[false, "form"]],
                context: {
                    ...this.props.context,
                    form_view_ref: this.props.expandedFormRef,
                },
            });
        }
    }
}
