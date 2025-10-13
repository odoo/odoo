import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";

export class LivechatSessionFormController extends FormController {
    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
    get thread() {
        return this.store.Thread.get({
            model: "discuss.channel",
            id: this.model.root.resId,
        });
    }
    displayName() {
        return this.thread?.displayName || super.displayName();
    }
}
