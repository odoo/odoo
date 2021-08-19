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
            this.messaging.browser.removeEventListener('resize', this._onResize);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Called when messaging is started.
         */
        start() {
            this.messaging.browser.addEventListener('resize', this._onResize);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _refresh() {
            this.update({
                globalWindowInnerHeight: this.messaging.browser.innerHeight,
                globalWindowInnerWidth: this.messaging.browser.innerWidth,
                isMobile: this.env.device.isMobile,
                sizeClass: this.env.device.size_class,
            });
        }
    }

    Device.fields = {
        globalWindowInnerHeight: attr(),
        globalWindowInnerWidth: attr(),
        isMobile: attr(),
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

    Device.modelName = 'mail.device';

    return Device;
}

registerNewModel('mail.device', factory);
