/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

import { browser } from '@web/core/browser/browser';

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
                globalWindowInnerHeight: browser.innerHeight,
                globalWindowInnerWidth: browser.innerWidth,
                isSmall: this.env.services.ui.isSmall,
            });
        }
    }

    Device.fields = {
        globalWindowInnerHeight: attr(),
        globalWindowInnerWidth: attr(),
        isSmall: attr(),
    };

    Device.modelName = 'mail.device';

    return Device;
}

registerNewModel('mail.device', factory);
