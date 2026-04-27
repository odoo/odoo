/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';

export class DialogWrapper extends Component {
    static template = xml`<div>
        <div class="o_tablet_popups">
            <t t-component="props.Component" t-props="props.componentProps" />
        </div>
    </div>`;

    static components = { Dialog };

    static props = {
        Component: { type: Function },
        componentProps: { type: Object, optional: true },
        close: { type: Function },
    };
}
