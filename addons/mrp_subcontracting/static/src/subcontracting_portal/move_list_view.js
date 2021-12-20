/** @odoo-module**/

import ListView from 'web.ListView';
import viewRegistry from 'web.view_registry';

const MoveListView = ListView.extend({
    searchMenuTypes: [],
});

viewRegistry.add('subcontracting_portal_move_list_view', MoveListView);

export default MoveListView;
