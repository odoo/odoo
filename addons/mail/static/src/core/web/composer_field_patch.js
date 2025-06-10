import { useService } from "@web/core/utils/hooks";
import { ComposerField } from "../common/composer_field";
import { HtmlComposer } from "./html_composer";
import { patch } from "@web/core/utils/patch";

Object.assign(ComposerField.components, { HtmlComposer });

patch(ComposerField.prototype, {
    setup() {
        super.setup(...arguments);
        this.composerSwitch = useService("mail.composer_switch_service");
    },
});
