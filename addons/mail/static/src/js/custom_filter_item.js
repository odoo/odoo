odoo.define('mail.CustomFilterItem', function (require) {
    "use strict";

    const CustomFilterItem = require('web.CustomFilterItem');
    const { patch } = require('web.utils');

    patch(CustomFilterItem.prototype, 'mail.CustomFilterItem', {

        /**
         * With the `mail` module installed, we want to filter out some of the
         * available fields in 'Add custom filter' menu (@see CustomFilterItem).
         * @override
         */
        _validateField(field) {
            return this._super(...arguments) &&
                field.relation !== 'mail.message' &&
                field.name !== 'message_ids';
        },
    });

    return CustomFilterItem;
});
