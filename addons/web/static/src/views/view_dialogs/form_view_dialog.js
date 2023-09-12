/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

import { Component, onMounted } from "@odoo/owl";

export class FormViewDialog extends Component {
    setup() {
        super.setup();

        this.modalRef = useChildRef();
        this.env.dialogData.dismiss = () => this.discardRecord();

        const buttonTemplate = this.props.isToMany
            ? "web.FormViewDialog.ToMany.buttons"
            : "web.FormViewDialog.ToOne.buttons";

        this.viewProps = {
            type: "form",
            buttonTemplate,

            context: this.props.context || {},
            display: { controlPanel: false },
            mode: this.props.mode || "edit",
            resId: this.props.resId || false,
            resModel: this.props.resModel,
            viewId: this.props.viewId || false,
            preventCreate: this.props.preventCreate,
            preventEdit: this.props.preventEdit,
            discardRecord: this.discardRecord.bind(this),
            saveRecord: async (record, { saveAndNew }) => {
                const saved = await record.save({ reload: false });
                if (saved) {
                    await this.props.onRecordSaved(record);
                    if (saveAndNew) {
                        const context = Object.assign({}, this.props.context);
                        Object.keys(context).forEach((k) => {
                            if (k.startsWith("default_")) {
                                delete context[k];
                            }
                        });
                        await record.model.load({ resId: false, context });
                    } else {
                        this.props.close();
                    }
                }
            },
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
}

FormViewDialog.components = { Dialog, View };
FormViewDialog.props = {
    close: Function,
    resModel: String,

    context: { type: Object, optional: true },
    mode: {
        optional: true,
        validate: (m) => ["edit", "readonly"].includes(m),
    },
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
FormViewDialog.defaultProps = {
    onRecordSaved: () => {},
    preventCreate: false,
    preventEdit: false,
    isToMany: false,
};
FormViewDialog.template = "web.FormViewDialog";
