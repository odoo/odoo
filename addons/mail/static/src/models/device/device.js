odoo.define('mail/static/src/models/device/device.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

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
                __mfield_globalWindowInnerHeight: this.env.browser.innerHeight,
                __mfield_globalWindowInnerWidth: this.env.browser.innerWidth,
                __mfield_isMobile: this.env.device.isMobile,
            });
        }
    }

    Device.fields = {
        __mfield_globalWindowInnerHeight: attr(),
        __mfield_globalWindowInnerWidth: attr(),
        __mfield_isMobile: attr(),
    };

    Device.modelName = 'mail.device';

    return Device;
}

registerNewModel('mail.device', factory);

});
