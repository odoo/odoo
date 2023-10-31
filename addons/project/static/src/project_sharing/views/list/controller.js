/** @odoo-module **/

import ListController from 'web.ListController';
import BasicController from 'web.BasicController';

export default ListController.extend({
    _getActionMenuItems: BasicController.prototype._getActionMenuItems,
});
