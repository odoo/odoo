/** @odoo-module */

import { registry } from "@web/core/registry";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";
import {
    append,
    createElement,
} from "@web/core/utils/xml";

function compileChatter(node, params) {
    node.classList.remove("oe_chatter");
    const container = createElement("div");
    container.classList.add("o_FormRenderer_chatterContainer");

    const chatter = createElement("ChatterContainer");
    chatter.setAttribute("threadModel", "props.record.resModel");
    chatter.setAttribute("threadId", "props.record.resId || undefined");
    // TODO: pass chatterFields equivalent in props

    // chatter.setAttribute("record", "props.record"); // props.record.model.load() to reload the form
    // in ChatterContainer setup:
    //   this.messagingService = useService("messaging");

    append(container, chatter);
    return container;
}

registry.category("form_compilers").add("chatter_compiler", {
    selector: "div.oe_chatter",
    fn: compileChatter,
});

FormRenderer.components.ChatterContainer = ChatterContainer;
