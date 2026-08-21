import { Component, props, types as t } from "@odoo/owl";

import { propComputed } from "@mail/utils/common/hooks";

export class CallTooltip extends Component {
    static template = "discuss.WarningTooltip";

    setup() {
        super.setup();
        this.id = propComputed("id", t.string());
        this.icon = propComputed("icon", t.string());
        this.iconClass = propComputed("iconClass", t.string().optional());
        this.headerText = propComputed("headerText", t.string());
        this.bodyText = propComputed("bodyText", t.string().optional());
        this.onDismiss = props.static("onDismiss", t.function());
        this.close = props.static("close", t.function().optional());
    }

    onClickClose() {
        this.onDismiss?.();
        this.close();
    }
}
