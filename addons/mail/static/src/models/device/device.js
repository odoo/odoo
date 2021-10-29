/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

function factory(dependencies) {

    class Device extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._refresh();
            this._onResize = _.debounce(() => this._refresh(), 100);
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            window.removeEventListener('resize', this._onResize);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Called when messaging is started.
         */
        start() {
            // TODO FIXME Not using this.env.browser because it's proxified, and
            // addEventListener does not work on proxified window. task-2234596
            window.addEventListener('resize', this._onResize);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _refresh() {
            this.update({
                globalWindowInnerHeight: this.env.browser.innerHeight,
                globalWindowInnerWidth: this.env.browser.innerWidth,
                isMobile: this.env.device.isMobile,
                isMobileDevice: this.messaging.device.isMobileDevice,
                sizeClass: this.env.device.size_class,
            });
        }
    }

    Device.fields = {
        globalWindowInnerHeight: attr(),
        globalWindowInnerWidth: attr(),
        /**
         * States whether this device has a small size (note: this field name is not ideal).
         */
        isMobile: attr(),
        /**
         * States whether this device is an actual mobile device.
         */
        isMobileDevice: attr(),
        /**
         * Size class of the device.
         *
         * This is an integer representation of the size.
         * Useful for conditional based on a device size, including
         * lower/higher. Device size classes are defined in sizeClasses
         * attribute.
         */
        sizeClass: attr(),
    };
    Device.identifyingFields = ['messaging'];
    Device.modelName = 'mail.device';

    return Device;
}

registerNewModel('mail.device', factory);
