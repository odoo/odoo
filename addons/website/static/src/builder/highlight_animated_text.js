import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useBus } from "@web/core/utils/hooks";

export class HighlightAnimatedText extends Component {
    static template = "website.HighlightAnimatedText";
    static components = { CheckBox };
    static props = [];

    setup() {
        this.state = useState({
            animatedTextHighlighted: this.isAnimatedTextHighlighted(),
            hasAnimatedText: this.hasAnimatedText(),
        });
        useBus(this.env.editorBus, "DOM_UPDATED", (ev) => {
            this.state.hasAnimatedText = this.hasAnimatedText();
        });
    }

    toggleAnimatedTextHighlight() {
        this.state.animatedTextHighlighted = this.env.editor.document.body.classList.toggle(
            "o_animated_text_highlighted"
        );
    }
    isAnimatedTextHighlighted() {
        return !!this.env.editor.document.body.classList.contains("o_animated_text_highlighted");
    }
    hasAnimatedText() {
        return !!this.env.editor.editable.querySelector(".o_animated_text");
    }
}
