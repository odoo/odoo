import { Component, onWillUpdateProps } from "@odoo/owl";

export class CommentAnchorText extends Component {
    static template = "knowledge.CommentAnchorText";
    static props = {
        anchorText: { String },
    };

    setup() {
        this.anchorTextArray = this.props.anchorText.split("<br>");
        onWillUpdateProps((newProps) => {
            this.anchorTextArray = newProps.anchorText.split("<br>");
        });
    }
}
