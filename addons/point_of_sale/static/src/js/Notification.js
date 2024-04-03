odoo.define('point_of_sale.Notification', function (require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    const { onMounted } = owl;

    class Notification extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.closeNotification);

            onMounted(() => {
                setTimeout(() => {
                    this.closeNotification();
                }, this.props.duration)
            });
        }
    }
    Notification.template = 'Notification';

    Registries.Component.add(Notification);

    return Notification;
});
