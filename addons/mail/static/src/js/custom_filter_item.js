odoo.define('mail.CustomFilterItem', function (require) {
    "use strict";

    const CustomFilterItem = require('web.CustomFilterItem');

    CustomFilterItem.patch('mail.CustomFilterItem', T => class extends T {

        /**
         * With the `mail` module installed, we want to filter out some of the
         * available fields in 'Add custom filter' menu (@see CustomFilterItem).
         * @override
         */
        _validateField(field) {
            return super._validateField(...arguments) &&
                field.relation !== 'mail.message' &&
                field.name !== 'message_ids';
        }
    });

    return CustomFilterItem;
});
