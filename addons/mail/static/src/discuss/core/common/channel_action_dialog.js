import { Component, xml } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";

export class ChannelActionDialog extends Component {
    static components = { Dialog };
    static props = ["title", "contentComponent", "contentProps", "close?", "contentClass?"];
    static template = xml`
        <Dialog size="'md'" title="props.title" footer="false" contentClass="'o-bg-body o-discuss-ChannelActionDialog '+ props.contentClass" bodyClass="'p-1'">
            <t t-component="props.contentComponent" t-props="props.contentProps"/>
        </Dialog>
    `;
}
