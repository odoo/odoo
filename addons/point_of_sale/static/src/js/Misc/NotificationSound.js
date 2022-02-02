odoo.define('point_of_sale.NotificationSound', function (require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class NotificationSound extends PosComponent {
        setup() {
            super.setup();
            useListener('ended', () => (this.props.sound.src = null));
        }
    }
    NotificationSound.template = 'NotificationSound';

    Registries.Component.add(NotificationSound);

    return NotificationSound;
});
