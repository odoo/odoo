/** @odoo-module **/

import '@mail/js/activity';

import field_registry from 'web.field_registry';

const KanbanActivity = field_registry.get('kanban_activity');

const ActivityCell = KanbanActivity.extend({});

export default ActivityCell;
