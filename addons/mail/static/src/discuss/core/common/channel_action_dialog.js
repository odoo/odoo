import { Component, props, t, xml } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";

export class ChannelActionDialog extends Component {
    static components = { Dialog };
    static template = xml`
        <Dialog closeOnClickAway="true" size="'md'" title="this.props.title" footer="false" contentClass="'o-bg-body o-discuss-ChannelActionDialog '+ this.props.contentClass" bodyClass="'p-1'">
            <t t-component="this.props.contentComponent" t-props="this.props.contentProps"/>
        </Dialog>
    `;

    setup() {
        super.setup(...arguments);
        this.props = props({
            contentClass: t.string().optional(),
            contentComponent: t.component(),
            contentProps: t.record(),
            title: t.string(),
        });
    }
}
