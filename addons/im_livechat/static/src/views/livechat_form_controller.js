import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";

export class LivechatSessionFormController extends FormController {
    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
    get channel() {
        return this.store["discuss.channel"].get(this.model.root.resId);
    }
    displayName() {
        return this.channel?.displayName || super.displayName();
    }
}
