import { useSignViewButtons } from "@sign/views/hooks";
import { useService } from "@web/core/utils/hooks";
import { useRef, Component } from "@odoo/owl";

export class SignActionHelper extends Component {
    static template = "sign.SignActionHelper";
    static props = [
        "resModel"
    ];

    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.fileInput = useRef("uploadFileInput");
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }

    onClickUpload(context) {
        return this.requestFile(context);
    }

    onClicksampleSign() {
        return this.actionService.doAction("sign.sign_template_tour_trigger_action");
    }
}
