/** @odoo-module **/

import FormController from 'web.FormController';
import BasicController from 'web.BasicController';

export default FormController.extend({
    _getActionMenuItems: BasicController.prototype._getActionMenuItems,
});
