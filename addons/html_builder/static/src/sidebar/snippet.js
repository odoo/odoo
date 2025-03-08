import { Component } from "@odoo/owl";

export class Snippet extends Component {
    static template = "html_builder.Snippet";
    static props = {
        snippetModel: { type: Object },
        snippet: { type: Object },
        onClickHandler: { type: Function },
        disabledTooltip: { type: String },
    };

    get snippet() {
        return this.props.snippet;
    }
}
