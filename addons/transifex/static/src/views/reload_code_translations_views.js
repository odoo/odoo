import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

export class TransifexCodeTranslationListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onClickReloadCodeTranslations() {
        await this.orm.call("transifex.code.translation", "reload", [], {});
        browser.location.reload();
    }
}

registry.category("views").add("transifex_code_translation_tree", {
    ...listView,
    Controller: TransifexCodeTranslationListController,
    buttonTemplate: "transifex.CodeTranslationListView.Buttons",
});
