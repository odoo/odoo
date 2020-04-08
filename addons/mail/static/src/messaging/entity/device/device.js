odoo.define('mail.messaging.entity.Device', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function DeviceFactory({ Entity }) {

    class Device extends Entity {

        /**
         * @override
         */
        static create() {
            const entity = super.create();
            entity._onResize = _.debounce(() => entity.update(), 100);
            return entity;
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Called when messaging is started.
         */
        start() {
            // not using this.env.window because it's proxified, and
            // addEventListener does not work on proxified window
            window.addEventListener('resize', this._onResize);
        }

        /**
         * Called when messaging is stopped.
         */
        stop() {
            window.removeEventListener('resize', this._onResize);
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
