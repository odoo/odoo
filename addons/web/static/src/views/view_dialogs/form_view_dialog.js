// @ts-check

/** @module @web/views/view_dialogs/form_view_dialog - Modal dialog embedding a full form view for creating or editing a single record */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";
import { Dialog } from "@web/ui/dialog/dialog";
import { View } from "@web/views/view";

/** Modal dialog embedding a full form view for creating or editing a single record, with save/discard/expand controls. */
export class FormViewDialog extends Component {
    static template = "web.FormViewDialog";
    static components = { Dialog, View };
    static props = {
        close: Function,
        resModel: String,

        context: { type: Object, optional: true },
        expandedFormRef: { type: String, optional: true },
        nextRecordsContext: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
        onRecordSaved: { type: Function, optional: true },
        onRecordSave: { type: Function, optional: true },
        onRecordDiscarded: { type: Function, optional: true },
        removeRecord: { type: Function, optional: true },
        resId: { type: [Number, Boolean], optional: true },
        title: { type: String, optional: true },
        viewId: { type: [Number, Boolean], optional: true },
        preventCreate: { type: Boolean, optional: true },
        preventEdit: { type: Boolean, optional: true },
        canExpand: { type: Boolean, optional: true },
        isToMany: { type: Boolean, optional: true },
        size: Dialog.props.size,
    };
    static defaultProps = {
        onRecordSaved: () => {},
        preventCreate: false,
        preventEdit: false,
        canExpand: true,
        isToMany: false,
    };

    setup() {
        super.setup();

        this.actionService = useService("action");
        this.modalRef = useChildRef();
        this.env.dialogData.dismiss = () => this.discardRecord();

        const buttonTemplate = this.props.isToMany
            ? "web.FormViewDialog.ToMany.buttons"
            : "web.FormViewDialog.ToOne.buttons";

        this.currentResId = this.props.resId;

        if (this.props.canExpand) {
            this.onExpandCallback = this.onExpand.bind(this);
        }

        this.viewProps = {
            type: "form",
            buttonTemplate,

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

    /** Invoke the onRecordDiscarded callback (if any) and close the dialog. */
    async discardRecord() {
        if (this.props.onRecordDiscarded) {
            await this.props.onRecordDiscarded();
        }
        this.props.close();
    }

    /** Navigate to a full-page form view for the current record, closing the dialog. */
    async onExpand() {
        const beforeLeaveCallbacks = this.viewProps.__beforeLeave__.callbacks;
        const res = await Promise.all(
            beforeLeaveCallbacks.map((callback) => callback()),
        );
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

registry.category("dialogs").add("form_view", FormViewDialog);
