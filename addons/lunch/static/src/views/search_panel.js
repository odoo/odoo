import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useService } from "@web/core/utils/hooks"
import { SIZES } from "@web/core/ui/ui_service";

export class LunchSearchPanel extends SearchPanel {
    setup() {
        super.setup();
        this.ui = useService('ui');
        this.state.sidebarExpanded = this.ui.size <= SIZES.LG ? false : true;
    }
}
