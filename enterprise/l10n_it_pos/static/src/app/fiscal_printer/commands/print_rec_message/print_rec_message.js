import { Component } from "@odoo/owl";

const Alignment = {
    LEFT: 1,
    CENTER: 2,
    RIGHT: 3,
};

export class PrintRecMessage extends Component {
    static template = "l10n_it_pos.PrintRecMessage";
    static props = {
        operator: { type: Number, optional: true },
        messageType: {
            type: Number,
            validate: (messageType) => 1 <= messageType && messageType <= 8,
        },
        index: { type: Number, optional: true, validate: (index) => index > 0 },
        font: { type: Number, optional: true },
        message: { type: String },
        alignment: {
            type: Number,
            validate: (alignment) => Object.values(Alignment).includes(alignment),
            optional: true,
        },
    };
    static defaultProps = {
        operator: 1,
        alignment: Alignment.LEFT,
    };

    get message() {
        const { messageType, message, alignment } = this.props;
        const MAX_CHARS = messageType === 4 ? 37 : 46;

        if (message.length >= MAX_CHARS) {
            return message;
        }

        let paddingLeft = 0;
        if (alignment === Alignment.CENTER) {
            paddingLeft = Math.floor((MAX_CHARS - message.length) / 2);
        } else if (alignment === Alignment.RIGHT) {
            paddingLeft = MAX_CHARS - message.length;
        }

        return " ".repeat(paddingLeft) + message;
    }
}
