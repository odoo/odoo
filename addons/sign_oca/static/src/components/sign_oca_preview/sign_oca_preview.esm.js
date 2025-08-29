/** @odoo-module QWeb **/
import {ControlPanel} from "@web/search/control_panel/control_panel";
import SignOcaPdfCommon from "../sign_oca_pdf_common/sign_oca_pdf_common.esm.js";
import {registry} from "@web/core/registry";

export default class SignOcaPreview extends SignOcaPdfCommon {
    setup() {
        this.res_id =
            this.props.action.params.res_id || this.props.action.context.active_id;
        this.model =
            this.props.action.params.res_model ||
            this.props.action.context.active_model;
        super.setup(...arguments);
    }
}
SignOcaPreview.template = "sign_oca.SignOcaPreview";
SignOcaPreview.components = {...SignOcaPdfCommon.components, ControlPanel};
SignOcaPreview.props = {
    action: Object,
    "*": {optional: true},
};
registry.category("actions").add("sign_oca_preview", SignOcaPreview);
