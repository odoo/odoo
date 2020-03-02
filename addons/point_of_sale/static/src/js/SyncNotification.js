odoo.define('point_of_sale.SyncNotification', function(require) {
    'use strict';

    const { useState } = owl;
    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent } = require('point_of_sale.PosComponent');

    // Previously SynchNotificationWidget
    class SyncNotification extends PosComponent {
        constructor() {
            super(...arguments);
            const synch = this.env.pos.get('synch');
            this.state = useState({ status: synch.status, msg: synch.pending });
        }
        mounted() {
            this.env.pos.on(
                'change:synch',
                (pos, synch) => {
                    this.state.status = synch.status;
                    this.state.msg = synch.pending;
                },
                this
            );
        }
        willUnmount() {
            this.env.pos.on('change:synch', null, this);
        }
        onClick() {
            this.env.pos.push_orders(null, { show_error: true });
        }
    }

    Chrome.addComponents([SyncNotification]);

    return { SyncNotification };
});
