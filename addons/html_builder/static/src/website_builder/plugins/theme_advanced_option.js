import { BaseOptionComponent } from "@html_builder/core/utils";
import { EditHeadBodyDialog } from "@website/components/edit_head_body_dialog/edit_head_body_dialog";
import { useService } from "@web/core/utils/hooks";

export class ThemeAdvancedOption extends BaseOptionComponent {
    static template = "html_builder.ThemeAdvancedOption";
    static props = {
        grays: Object,
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    openCustomCodeDialog() {
        this.dialog.add(EditHeadBodyDialog);
    }
    configureApiKey() {
        // TODO After GMap options are merged.
    }
}
