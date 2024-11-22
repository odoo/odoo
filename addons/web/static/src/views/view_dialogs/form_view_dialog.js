import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/search/action_hook";
import { View } from "@web/views/view";

import { Component, onMounted } from "@odoo/owl";

export class FormViewDialog extends Component {
    static template = "web.FormViewDialog";
    static components = { Dialog, View };
    static props = {
        close: Function,
        resModel: String,

        context: { type: Object, optional: true },
        nextRecordsContext: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
        onRecordSaved: { type: Function, optional: true },
        onRecordDiscarded: { type: Function, optional: true },
        removeRecord: { type: Function, optional: true },
        resId: { type: [Number, Boolean], optional: true },
        title: { type: String, optional: true },
        viewId: { type: [Number, Boolean], optional: true },
        preventCreate: { type: Boolean, optional: true },
        preventEdit: { type: Boolean, optional: true },
        isToMany: { type: Boolean, optional: true },
        size: Dialog.props.size,
    };
    static defaultProps = {
        onRecordSaved: () => {},
        preventCreate: false,
        preventEdit: false,
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
            saveRecord: async (record, { saveAndNew }) => {
                const saved = await record.save({ reload: false });
                if (saved) {
                    this.currentResId = record.resId;
                    await this.props.onRecordSaved(record);
                    if (saveAndNew) {
                        this.currentResId = false;
                        const context = this.props.nextRecordsContext || this.props.context || {};
                        await record.model.load({ resId: false, context });
                    } else {
                        this.props.close();
                    }
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

        onMounted(() => {
            if (this.modalRef.el.querySelector(".modal-footer").childElementCount > 1) {
                const defaultButton = this.modalRef.el.querySelector(
                    ".modal-footer button.o-default-button"
                );
                if (defaultButton) {
                    defaultButton.classList.add("d-none");
                }
            }
        });
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
            });
        }
    }
}
