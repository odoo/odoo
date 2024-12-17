import { ListController } from "@web/views/list/list_controller";
import { PurchaseFileUploader } from "@purchase/components/purchase_file_uploader/purchase_file_uploader";

export class PurchaseListController extends ListController {
    static template = "purchase.PurchaseListController";
    static components = {
        ...ListController.components,
        PurchaseFileUploader,
    };

    setup() {
        super.setup();
    }

}
