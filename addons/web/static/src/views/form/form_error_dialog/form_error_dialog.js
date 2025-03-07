import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class FormErrorDialog extends Component {
<<<<<<< saas-17.4
    static template = "web.FormErrorDialog";
    static components = { Dialog };
    static props = {
        message: { type: String, optional: true },
        onDiscard: Function,
        onStayHere: Function,
        close: Function,
    };
||||||| 0789a962a45adb5a038cb86e62de2b4f657a2762
=======
    setup() {
        this.action = useService("action");
        this.message = this.props.message;
        if (this.props.data.name === "odoo.exceptions.RedirectWarning") {
            this.message = this.props.data.arguments[0];
            this.redirectAction = this.props.data.arguments[1];
            this.redirectBtnLabel = this.props.data.arguments[2];
        }
    }

    onRedirectBtnClicked() {
        this.action.doAction(this.redirectAction);
    }

>>>>>>> 0ec87c774743fcaf058190df0b0e09854782e0fb
    async discard() {
        await this.props.onDiscard();
        this.props.close();
    }

    async stay() {
        await this.props.onStayHere();
        this.props.close();
    }
}
