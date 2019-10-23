odoo.define('mail.widget.OwlMixin', function () {
'use strict';

/**
 * Odoo Widget, necessary to instantiate a root OWL widget.
 */
const OwlMixin = {
    getEnv() {
        return this.call('owl', 'getEnv');
    },
};

return OwlMixin;

});
