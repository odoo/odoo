import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class QuestionDialog extends Component {
    static template = "pos_tyro.QuestionDialog";
    static components = { Dialog };
    static props = {
        question: {
            type: Object,
            shape: {
                text: String,
                options: { type: Array, element: String },
                isError: { type: Boolean, optional: true },
                isManualCancel: { type: Boolean, optional: true },
            },
        },
        onClickAnswer: Function,
        close: Function,
    };

    onClickOption(option) {
        this.props.onClickAnswer(option);
        this.props.close();
    }
}
