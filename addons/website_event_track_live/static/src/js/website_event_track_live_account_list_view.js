import { EventTrackLiveAccountListController } from './website_event_track_live_account_list_controller';

import { listView } from '@web/views/list/list_view';
import { registry } from '@web/core/registry';

export const EventTrackLiveAccountListView = {
    ...listView,
    Controller: EventTrackLiveAccountListController,
    buttonTemplate: 'EventTrackLiveAccountListView.buttons',
};

registry.category("views").add("event_track_live_account_list_view", EventTrackLiveAccountListView);
