odoo.define('mail.messaging.entity.Device', function (require) {
'use strict';

const {
    fields: {
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

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
            // TODO FIXME Not using this.env.window because it's proxified, and
            // addEventListener does not work on proxified window. task-2234596
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
            Object.assign(this, {
                globalWindowInnerHeight: this.env.window.innerHeight,
                globalWindowInnerWidth: this.env.window.innerWidth,
                isMobile: this.env.device.isMobile,
            });
        }

    }

    Object.assign(Device, {
        fields: Object.assign({}, Entity.fields, {
            messaging: one2one('Messaging', {
                inverse: 'device',
            }),
        }),
    });

    return Device;
}

registerNewEntity('Device', DeviceFactory);

});
