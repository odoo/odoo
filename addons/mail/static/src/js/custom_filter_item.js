/** @odoo-module **/

import CustomFilterItem from 'web.CustomFilterItem';
import { patch } from 'web.utils';

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

export default CustomFilterItem;
