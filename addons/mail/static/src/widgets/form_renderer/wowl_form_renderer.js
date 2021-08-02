/** @odoo-module */

import { registry } from "@web/core/registry";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';

function compileChatter(node, params) {
    node.classList.remove("oe_chatter");
    const container = this.document.createElement("div");
    container.classList.add("o_FormRenderer_chatterContainer");

    const chatter = this.document.createElement("ChatterContainer");
    chatter.setAttribute("threadModel", "props.model.resModel");
    chatter.setAttribute("threadId", "props.model.resId");
    // TODO: pass chatterFields equivalent in props

    this.append(container, chatter);
    return container;
}

registry.category("form_compilers").add("chatter_compiler", {
    tag: "div",
    class: "oe_chatter",
    fn: compileChatter,
});

class ChatterContainerLegacy extends owl.Component {
    setup() {
        this.env = owl.Component.env;
    }
}
ChatterContainerLegacy.template = owl.tags.xml`<ChatterContainer t-props="props"/>`;
ChatterContainerLegacy.components = { ChatterContainer };

FormRenderer.components.ChatterContainer = ChatterContainerLegacy;
