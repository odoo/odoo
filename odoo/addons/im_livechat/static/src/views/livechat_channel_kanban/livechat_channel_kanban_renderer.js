/* @odoo-module */

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { LivechatChannelKanbanRecord } from "./livechat_channel_kanban_record";

export class LivechatChannelKanbanRenderer extends KanbanRenderer {}

LivechatChannelKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: LivechatChannelKanbanRecord,
};
