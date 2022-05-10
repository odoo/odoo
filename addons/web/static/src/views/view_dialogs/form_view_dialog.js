/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";
import { View } from "@web/views/view";

const { Component, useEffect } = owl;

export class FormViewDialog extends Component {
    setup() {
        super.setup();

        this.modalRef = useChildRef();

        this.viewProps = {
            type: "form",

            context: this.props.context || {},
            display: {
                controlPanel: { "bottom-right": false }, // TODO? remove completely the control panel?
            },
            mode: this.props.mode || "edit",
            resId: this.props.resId || false,
            resModel: this.props.resModel,
            viewId: this.props.viewId || false,

            discardRecord: () => {
                this.props.close();
            },
            saveRecord: async (record) => {
                const saved = await record.save({ stayInEdition: true, noReload: true });
                if (saved) {
                    if (this.props.onRecordSaved) {
                        await this.props.onRecordSaved(record);
                    }
                    this.props.close();
                }
            },
        };

        useEffect(
            () => {
                if (this.modalRef.el.querySelector(".modal-footer").childElementCount > 1) {
                    const defaultButton = this.modalRef.el.querySelector(
                        ".modal-footer button.o-default-button"
                    );
                    defaultButton.classList.add("d-none");
                }
            },
            () => []
        );
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
    resId: { type: [Number, false], optional: true },
    title: { type: String, optional: true },
    viewId: { type: [Number, false], optional: true },
};
FormViewDialog.template = "web.FormViewDialog";
