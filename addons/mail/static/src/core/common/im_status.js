import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { getImStatusClass, useImStatusData } from "./im_status_data";

export class ImStatus extends Component {
    static props = ["persona?", "className?", "style?", "member?", "slots?", "size?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg" };
    static components = { Typing };

    setup() {
        super.setup();
        this.imStatusData = useImStatusData();
    }

    get persona() {
        return this.props.persona ?? this.props.member?.persona;
    }

    get colorClass() {
        return getImStatusClass(this.persona.im_status);
    }
}
