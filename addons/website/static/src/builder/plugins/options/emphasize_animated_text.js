import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useBus } from "@web/core/utils/hooks";

export class EmphasizeAnimatedText extends Component {
    static template = "website.EmphasizeAnimatedText";
    static components = { CheckBox };
    static props = [];

    setup() {
        this.state = useState({
            animatedTextEmphasized: this.isAnimatedTextEmphasized(),
            hasAnimatedText: this.hasAnimatedText(),
        });
        useBus(this.env.editorBus, "DOM_UPDATED", (ev) => {
            this.state.hasAnimatedText = this.hasAnimatedText();
        });
    }

    toggleEmphasizeAnimatedText() {
        this.state.animatedTextEmphasized = this.env.editor.document.body.classList.toggle(
            "o_animated_text_emphasized"
        );
    }

    isAnimatedTextEmphasized() {
        return !!this.env.editor.document.body.classList.contains("o_animated_text_emphasized");
    }

    hasAnimatedText() {
        return !!this.env.editor.editable.querySelector(".o_animated_text");
    }
}
