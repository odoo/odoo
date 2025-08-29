/** @odoo-module */
/* Copyright 2024 Tecnativa - Carlos Roca
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {Dialog} from "@web/core/dialog/dialog";
import {useChildRef} from "@web/core/utils/hooks";

import {Component} from "@odoo/owl";

export class SignOcaConfigureFieldDialog extends Component {
    setup() {
        this.env.dialogData.dismiss = () => this._cancel();
        this.modalRef = useChildRef();
        this.isProcess = false;
    }

    async _cancel() {
        this.props.close();
    }

    async _confirm() {
        const $el = $(this.modalRef.el);
        await this.props.confirm(
            parseInt($el.find('select[name="field_id"]').val(), 10),
            parseInt($el.find('select[name="role_id"]').val(), 10),
            $el.find("input[name='required']").prop("checked"),
            $el.find("input[name='placeholder']").val()
        );
        this.props.close();
    }

    async _delete() {
        this.props.delete();
        this.props.close();
    }
}
SignOcaConfigureFieldDialog.template = "sign_oca.SignOcaConfigureFieldDialog";
SignOcaConfigureFieldDialog.components = {Dialog};
SignOcaConfigureFieldDialog.props = {
    close: Function,
    title: {
        validate: (m) => {
            return (
                typeof m === "string" ||
                (typeof m === "object" && typeof m.toString === "function")
            );
        },
    },
    item: Object,
    info: Object,
    confirm: Function,
    delete: Function,
};
