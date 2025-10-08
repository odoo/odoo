import { Component } from '@odoo/owl';

export class WarningNotification extends Component {
    static template = 'website_sale.WarningNotification';
    static props = {
        warning_message: String,
    }
}
