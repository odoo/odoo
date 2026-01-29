import { Component, props, types } from "@odoo/owl";

export class CallSuggestionTooltip extends Component {
    static template = "discuss.CallSuggestionTooltip";
    props = props({
        id: types.string(),
        iconClass: types.string(),
        headerText: types.string(),
        bodyText: types.string(),
        onDismiss: types.function([]),
        close: types.function([]),
    });
}
