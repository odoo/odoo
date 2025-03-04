import { ListController } from "@web/views/list/list_controller";
import { useService } from '@web/core/utils/hooks';

export class EventTrackLiveAccountListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService('orm');
    }

    _onAddYoutubeAccount() {
        this.orm.call('event.track.live.account', 'add_youtube_account', [[]],
            {}).then((action) => {
            document.location = action.url;
        });
    }
}
