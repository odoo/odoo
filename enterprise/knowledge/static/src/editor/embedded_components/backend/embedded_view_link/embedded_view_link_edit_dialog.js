import { Component, useState, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { EMBEDDED_VIEW_LINK_STYLES } from "@knowledge/editor/embedded_components/core/embedded_view_link/embedded_view_link_style";

export class EmbeddedViewLinkEditDialog extends Component {
    static template = "knowledge.EmbeddedViewLinkEditDialog";
    static components = { Dialog };
    static props = {
        style: { type: String },
        close: { type: Function },
        name: { type: String },
        onSave: { type: Function },
    };

    setup() {
        this.state = useState({
            name: this.props.name,
            style: this.props.style,
        });
        this.input = useRef("input");
    }

    //--------------------------------------------------------------------------
    // GETTERS/SETTERS
    //--------------------------------------------------------------------------

    get name() {
        return this.state.name.trim();
    }

    get styles() {
        return EMBEDDED_VIEW_LINK_STYLES;
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    onConfirm() {
        if (!this.name) {
            return this.input.el.focus();
        }
        this.props.onSave(this.name, this.state.style);
        this.props.close();
    }

    updateStyle(style) {
        this.state.style = style;
    }
}
