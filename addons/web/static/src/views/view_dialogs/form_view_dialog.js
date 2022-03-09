/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormArchParser, loadSubViews } from "@web/views/form/form_view";
import { ViewCompiler } from "../helpers/view_compiler";
import { ViewButton } from "@web/views/view_button/view_button";
import { useModel } from "../helpers/model";
import { RelationalModel } from "../relational_model";

const { onWillStart, useRef, xml } = owl;

const templateFooter = Object.create(null);

export class FormViewDialog extends Dialog {
    setup() {
        super.setup();
        this.viewService = useService("view");
        this.user = useService("user");
        this.archInfo = this.props.archInfo;
        this.title = this.props.title;
        this.record = this.props.record;
        this.multiSelect = false;
        this.buttons = this.props.buttons;

        this.dialogFooterRef = useRef("dialogFooter");

        if (!this.record) {
            this.model = useModel(RelationalModel, {
                resModel: this.props.resModel,
                resId: this.props.resId,
                resIds: this.props.resIds,
                viewMode: "form",
                rootType: "record",
            });
        } else {
            this.model = this.record.model;
        }

        onWillStart(async () => {
            if (!this.archInfo) {
                const { form } = await this.viewService.loadViews({
                    resModel: this.record ? this.record.resModel : this.props.resModel,
                    context: this.record ? this.record.context : this.props.context || {},
                    views: [[this.props.viewId || false, "form"]],
                });
                const archInfo = new FormArchParser().parse(form.arch, form.fields);
                this.archInfo = {
                    ...archInfo,
                    fields: form.fields,
                };
            }

            if (!this.record) {
                this.record = this.model.root;
            }

            this.createButtons();

            Object.assign(this.record.activeFields, this.archInfo.activeFields);
            Object.assign(this.record.fields, this.archInfo.fields);
            this.record.fieldNames = Object.keys(this.record.activeFields);
            //FIXME: Maybe we need to check if multiple footer
            if (this.archInfo.xmlDoc.querySelector("footer")) {
                const footerXmlDoc = this.archInfo.xmlDoc.querySelector("footer");
                const templateKey = footerXmlDoc.outerXml;

                if (!templateFooter[templateKey]) {
                    const { qweb } = this.env;
                    const compiledDoc = new ViewCompiler(qweb, this.archInfo.fields).compile(
                        footerXmlDoc
                    );
                    templateFooter[templateKey] = xml`${compiledDoc.outerHTML}`;
                }

                this.footerTemplate = templateFooter[templateKey];
                this.archInfo.xmlDoc.querySelector("footer").remove();
                this.archInfo.arch = this.archInfo.xmlDoc.outerXml;
            }
            await loadSubViews(
                this.archInfo.activeFields,
                this.archInfo.fields,
                this.record ? this.record.context : this.props.context || {},
                this.record.resModel,
                this.viewService,
                this.user
            );
            await this.record.load();
        });
    }

    async buttonClick(onClick, close) {
        if (onClick) {
            await onClick();
        }
        if (close) {
            this.close();
        }
    }

    createButtons() {
        if (this.buttons) {
            return;
        }
        const readonly = !this.record.isInEdition;
        const multiSelect = this.record.resId === -1 && !this.props.disableMultipleSelection;
        this.buttons = [
            {
                text:
                    this.props.closeText ||
                    (readonly ? this.env._t("Close") : this.env._t("Discard")),
                className: "btn-secondary o_form_button_cancel",
                hotkey: "j",
                close: true,
                onClick: () => {
                    if (!readonly) {
                        this.model.root.discard();
                    }
                },
            },
        ];
        if (!readonly) {
            this.buttons.unshift({
                text:
                    this.props.saveText ||
                    (multiSelect ? this.env._t("Save & Close") : this.env._t("Save")),
                className: "btn-primary",
                hotkey: "c",
                close: true,
                onClick: async () => {
                    if (this.props.save) {
                        await this.props.save();
                    }
                },
            });

            if (multiSelect) {
                this.buttons.splice(1, 0, {
                    text: this.env._t("Save & New"),
                    className: "btn-primary",
                    hotkey: "n",
                    onClick: async () => {
                        const disabledButtons = this.disableButtons();
                        await this.model.root.save();
                        await this.model.load({ resId: null });
                        this.enableButtons(disabledButtons);
                        this.title && this.title.replace(this.env._t("Open:"), this.env._t("New:"));
                    },
                });
            }
        }
    }

    disableButtons() {
        const btns = this.dialogFooterRef.el.querySelectorAll(".o_cp_buttons button");
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        return btns;
    }
    enableButtons(btns) {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
    }
}
FormViewDialog.bodyTemplate = "web.FormViewDialogBody";
FormViewDialog.footerTemplate = "web.FormViewDialogFooter";
FormViewDialog.components = { FormRenderer, ViewButton };
FormViewDialog.contentClass = "o_form_view_dialog";
FormViewDialog.props = {
    ...Dialog.props,
    archInfo: { type: Object, optional: true },
    title: { type: String, optional: true },
    record: { type: Object, optional: true },
    buttons: { type: Array, optional: true },
    resModel: { type: String, optional: true },
    resId: { type: Number, optional: true },
    resIds: { type: Array, optional: true },
    context: { type: Object, optional: true },
    viewId: { type: String, optional: true },
    disableMultipleSelection: { type: Boolean, optional: true },
    closeText: { type: String, optional: true },
    saveText: { type: String, optional: true },
    save: { type: Function, optional: true },
};
