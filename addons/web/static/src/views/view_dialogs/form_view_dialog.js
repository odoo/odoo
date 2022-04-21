/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { createElement } from "@web/core/utils/xml";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormArchParser, loadSubViews } from "@web/views/form/form_view";
import { ViewButton } from "@web/views/view_button/view_button";
import { useModel } from "../helpers/model";
import { RelationalModel } from "../relational_model";
import { useViewButtons } from "@web/views/view_button/hook";

const { onWillStart } = owl;

export class FormViewDialog extends Dialog {
    setup() {
        super.setup();
        this.viewService = useService("view");
        this.user = useService("user");
        this.archInfo = this.props.archInfo;
        this.title = this.props.title;
        this.record = this.props.record;

        if (!this.record) {
            this.model = useModel(RelationalModel, {
                resModel: this.props.resModel,
                resId: this.props.resId,
                resIds: this.props.resIds,
                viewMode: "form",
                rootType: "record",
                mode: this.props.mode,
            });
        } else {
            this.model = this.record.model;
        }
        useViewButtons(this.model);

        onWillStart(async () => {
            if (!this.archInfo) {
                const { fields, views } = await this.viewService.loadViews({
                    resModel: this.record ? this.record.resModel : this.props.resModel,
                    context: this.record ? this.record.context : this.props.context || {},
                    views: [[this.props.viewId || false, "form"]],
                });
                const archInfo = new FormArchParser().parse(views.form.arch, fields);
                this.archInfo = { ...archInfo, fields };
            }

            if (!this.record) {
                await this.model.isLoaded;
                this.record = this.model.root;
                this.record.activeFields = {
                    ...this.record.activeFields,
                    ...this.archInfo.activeFields,
                };
                this.record.fields = { ...this.record.fields, ...this.archInfo.fields };
                await loadSubViews(
                    this.archInfo.activeFields,
                    this.archInfo.fields,
                    this.record ? this.record.context : this.props.context || {},
                    this.record.resModel,
                    this.viewService,
                    this.user
                );
                await this.record.load();
            }

            this.readonly = !this.record.isInEdition;
            this.multiSelect = this.record.resId === false && !this.props.disableMultipleSelection;

            if (this.archInfo.xmlDoc.querySelector("footer")) {
                this.footerArchInfo = Object.assign({}, this.archInfo);
                this.footerArchInfo.xmlDoc = createElement("t");
                this.footerArchInfo.xmlDoc.append(
                    ...[...this.archInfo.xmlDoc.querySelectorAll("footer")]
                );
                this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
                [...this.archInfo.xmlDoc.querySelectorAll("footer")].forEach((x) => x.remove());
                this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
            }
        });
    }

    discard() {
        if (this.record.isInEdition) {
            this.record.discard();
        }
        this.close();
    }

    async save({ saveAndNew }) {
        if (this.props.save) {
            if (this.record.checkValidity()) {
                this.record = await this.props.save(this.record, { saveAndNew });
            } else {
                return false;
            }
        }
        if (!saveAndNew) {
            this.close();
        }
        return true;
    }

    async saveAndNew() {
        const disabledButtons = this.disableButtons();
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            if (!this.props.record) {
                await this.model.load({ resId: null });
                this.record = this.model.root;
            }
            this.readonly = !this.record.isInEdition;
            this.multiSelect = this.record.resId === false && !this.props.disableMultipleSelection;

            this.enableButtons(disabledButtons);
            if (this.title) {
                this.title.replace(this.env._t("Open:"), this.env._t("New:"));
            }
            this.render(true);
        }
    }

    disableButtons() {
        const btns = this.modalRef.el.querySelectorAll(".modal-footer button");
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
    viewId: { type: [Number, false], optional: true },
    disableMultipleSelection: { type: Boolean, optional: true },
    mode: { type: String, optional: true },
    closeText: { type: String, optional: true },
    saveText: { type: String, optional: true },
    save: { type: Function, optional: true },
};
