<<<<<<< 18.0
import { FormRendererWithHtmlExpander } from "@resource/views/form_with_html_expander/form_renderer_with_html_expander";
import { useBus } from "@web/core/utils/hooks";

export class TodoFormRenderer extends FormRendererWithHtmlExpander {
    setup() {
        super.setup();
        useBus(this.env.bus, "TODO:TOGGLE_CHATTER", this.toggleChatter);
        this.sizeToExpandHTMLField = 1;
    }

    toggleChatter(ev) {
        this.sizeToExpandHTMLField = ev.detail.displayChatter ? 6 : 1;
    }

    _canExpandHTMLField(size) {
        return size >= this.sizeToExpandHTMLField;
    }
||||||| 1fb35add8090b5fc9e706aad67f6bb38432273e0
=======
/* @odoo-module */

import { FormRenderer } from "@web/views/form/form_renderer";

import { TodoFormStatusBarButtons } from "./todo_form_status_bar_button";

export class TodoFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        StatusBarButtons: TodoFormStatusBarButtons,
    };
>>>>>>> da59bf1857979ad7dae5008bc3c832ae6619a517
}
