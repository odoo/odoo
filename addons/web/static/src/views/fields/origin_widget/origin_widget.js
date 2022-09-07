/** @odoo-module **/

import { registry } from '@web/core/registry';

const { Component } = owl;

export class OriginWidget extends Component {
    setup() {
        const { data } = this.props.record
        origin = data.origin || data.invoice_origin
        try {
            this.origins = JSON.parse(origin);
        } catch (_) {
            this.origins = [{
                'name': origin
            }];
        }
    }
}

OriginWidget.template = "origin.widget"
OriginWidget.displayName = "Origin widget"

registry.category('fields').add('origin_widget', OriginWidget);