odoo.define('point_of_sale.Notification', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class Notification extends PosComponent {
        constructor() {
            super(...arguments)
            useListener('click', this.closeNotification);
        }
        mounted() {
            setTimeout(() => {
                this.closeNotification();
            }, this.props.duration)
        }
    }
    Notification.template = 'Notification';

    Registries.Component.add(Notification);

    return Notification;
});
