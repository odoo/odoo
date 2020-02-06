odoo.define('mail.messaging.entity.Device', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function DeviceFactory({ Entity }) {

    class Device extends Entity {

        start() {
            this.env.window.addEventListener('resize', _.debounce(() => this.update()), 100);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update() {
            this._write({
                globalWindowInnerHeight: this.env.window.innerHeight,
                globalWindowInnerWidth: this.env.window.innerWidth,
                isMobile: this.env.device.isMobile,
            });
        }

    }

    Object.assign(Device, {
        relations: Object.assign({}, Entity.relations, {
            messaging: {
                inverse: 'device',
                to: 'Messaging',
                type: 'one2one',
            },
        }),
    });

    return Device;
}

registerNewEntity('Device', DeviceFactory);

});
