import { Component, proxy, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useBus } from "@web/core/utils/hooks";

export class EmphasizeAnimatedContent extends Component {
    static template = "website.EmphasizeAnimatedContent";
    static components = { CheckBox };
    props = useProps({});

    setup() {
        this.state = proxy({
            animatedContentEmphasized: this.isAnimatedContentEmphasized(),
            hasAnimatedContent: this.hasAnimatedContent(),
        });
        useBus(this.env.editorBus, "DOM_UPDATED", (ev) => {
            this.state.hasAnimatedContent = this.hasAnimatedContent();
        });
    }

    toggleEmphasizeAnimatedContent() {
        this.state.animatedContentEmphasized = this.env.editor.document.body.classList.toggle(
            "o_animated_content_emphasized"
        );
    }

    isAnimatedContentEmphasized() {
        return !!this.env.editor.document.body.classList.contains("o_animated_content_emphasized");
    }

    hasAnimatedContent() {
        return !!this.env.editor.editable.querySelector(".o_animate");
    }
}
