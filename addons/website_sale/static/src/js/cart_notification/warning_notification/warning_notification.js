import { Component, t, useProps } from '@odoo/owl';

export class WarningNotification extends Component {
    static template = 'website_sale.WarningNotification';
    props = useProps({
        warning_message: t.string(),
    });
}
