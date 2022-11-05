/** @odoo-module **/

import { useRefToModel } from "@mail/component_hooks/use_ref_to_model";
import { registerMessagingComponent } from "@mail/utils/messaging_component";

import { Component } from "@odoo/owl";

export class ActivityCellView extends Component {
    setup() {
        useRefToModel({ fieldName: "contentRef", refName: "content" });
    }

    get activityCellView() {
        return this.props.record;
    }
}

Object.assign(ActivityCellView, {
    props: { record: Object },
    template: "mail.ActivityCellView",
});

registerMessagingComponent(ActivityCellView);
