import { propComputed } from "@mail/utils/common/hooks";

import { Component, props, t } from "@odoo/owl";

export class CallSuggestionTooltip extends Component {
    static template = "discuss.CallSuggestionTooltip";

    setup() {
        super.setup();
        this.id = propComputed("id", t.string());
        this.iconClass = propComputed("iconClass", t.string().optional());
        this.headerText = propComputed("headerText", t.string());
        this.bodyText = propComputed("bodyText", t.string().optional());
        this.onDismiss = props.static("onDismiss", t.function([]));
        this.close = props.static("close", t.function([]).optional());
    }
}
