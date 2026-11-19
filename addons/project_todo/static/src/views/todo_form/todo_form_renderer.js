import { FormRendererWithHtmlExpander } from "@resource/views/form_with_html_expander/form_renderer_with_html_expander";
import { SIZES } from "@web/core/ui/ui_utils";
import { useBus } from "@web/core/utils/hooks";

export class TodoFormRenderer extends FormRendererWithHtmlExpander {
    setup() {
        super.setup();
        useBus(this.env.bus, "TODO:TOGGLE_CHATTER", this.toggleChatter.bind(this));
        this.sizeToExpandHTMLField = SIZES.SM;
    }

    toggleChatter(ev) {
        this.sizeToExpandHTMLField = ev.detail.displayChatter ? SIZES.XXL : SIZES.SM;
    }

    _canExpandHTMLField(size) {
        return size >= this.sizeToExpandHTMLField;
    }
}
