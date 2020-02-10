odoo.define('point_of_sale.SyncNotification', function(require) {
    'use strict';

    const { useState } = owl;
    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent } = require('point_of_sale.PosComponent');

    // Previously SynchNotificationWidget
    class SyncNotification extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ status: 'connected', msg: 0 });
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
            this.env.pos.push_order(null, { show_error: true });
        }
    }

    Chrome.addComponents([SyncNotification]);

    return { SyncNotification };
});
