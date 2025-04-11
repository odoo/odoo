import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

export class ArchiveDisabledListController extends ListController {
    setup() {
        super.setup();
        this.archiveEnabled = false;
        this.store = useService("mail.store")
    }

    async createRecord() {
        console.log("button pressed")
        return this.store.scheduleActivity(
            this.props.resModel != "mail.activity" ? this.props.resModel : false,
            //this.props.resModel,
            false
        )
        //return super.onClickCreate()
    }

    async openRecord() {
        console.log("openRecord")
        return super.openRecord(...arguments)
    }
}
