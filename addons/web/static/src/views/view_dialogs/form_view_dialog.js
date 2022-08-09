/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";
import { LegacyFormViewInDialogError, View } from "@web/views/view";
import { FormViewDialog as LegacyFormViewDialog } from "web.view_dialogs";
import { standaloneAdapter } from "web.OwlCompatibility";

const { Component, onError, onMounted, onWillDestroy, useState } = owl;

export class FormViewDialog extends Component {
    setup() {
        super.setup();

        this.modalRef = useChildRef();

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
            discardRecord: () => {
                this.props.close();
            },
            saveRecord: async (record, { saveAndNew }) => {
                const saved = await record.save({ stayInEdition: true, noReload: true });
                if (saved) {
                    await this.props.onRecordSaved(record);
                    if (saveAndNew) {
                        const context = Object.assign({}, this.props.context);
                        Object.keys(context).forEach((k) => {
                            if (k.startsWith("default_")) {
                                delete context[k];
                            }
                        });
                        await record.model.load({ resId: null, context });
                    } else {
                        this.props.close();
                    }
                }
            },
        };

        onMounted(() => {
            if (
                !this.state.error &&
                this.modalRef.el.querySelector(".modal-footer").childElementCount > 1
            ) {
                const defaultButton = this.modalRef.el.querySelector(
                    ".modal-footer button.o-default-button"
                );
                if (defaultButton) {
                    defaultButton.classList.add("d-none");
                }
            }
        });

        // FIXME: If the form view to instantiate is a js_class that hasn't been converted yet,
        // we can't use the new FormViewDialog, as it would instantiate the legacy form view. As
        // a consequence, the control panel buttons would not be moved to the footer. In this case,
        // View triggers an error that we catch here, and we spawn a legacy FormViewDialog instead.
        this.state = useState({ error: null });
        this.dialogClose = [];
        onError((e) => {
            if (e.cause instanceof LegacyFormViewInDialogError) {
                this.state.error = e.cause;
                const adapterParent = standaloneAdapter({ Component });
                const dialog = new LegacyFormViewDialog(adapterParent, {
                    res_id: this.props.resId,
                    res_model: this.props.resModel,
                    view_id: this.props.viewId,
                    context: this.props.context || {},
                    title: this.props.title,
                    disable_multiple_selection: true,
                    on_saved: async (record) => {
                        await this.props.onRecordSaved(record);
                        this.props.close();
                    },
                });
                dialog.open();
                this.dialogClose.push(() => dialog.close());
                return;
            }
            throw e;
        });
        onWillDestroy(() => {
            this.dialogClose.forEach((close) => close());
        });
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
