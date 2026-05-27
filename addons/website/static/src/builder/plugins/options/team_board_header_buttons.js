import { Component } from "@odoo/owl";
import { useOperation } from "@html_builder/core/operation_plugin";

export class TeamBoardHeaderMiddleButtons extends Component {
    static template = "website.TeamBoardHeaderMiddleButtons";
    static props = {
        addBoard: Function,
    };

    setup() {
        this.callOperation = useOperation();
    }

    onAddBoard() {
        this.callOperation(() => this.props.addBoard(this.env.getEditingElement()));
    }
}
