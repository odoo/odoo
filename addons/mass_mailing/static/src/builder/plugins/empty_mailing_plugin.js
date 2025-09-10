import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class EmptyMailingPlugin extends Plugin {
    static id = "EmptyMailing";
    static dependencies = [
        "baseContainer",
        "builderOptions",
        "disableSnippets",
        "history",
        "selection",
    ];

    resources = {
        beforeinput_handlers: withSequence(1, this.ensureTextBlock.bind(this)),
    };

    ensureTextBlock() {
        const wrapperTd = this.editable.querySelector(".o_mail_wrapper_td");
        if (!wrapperTd) {
            return;
        }
        const { anchorNode } = this.dependencies.selection.getEditableSelection();
        if (anchorNode === wrapperTd && !wrapperTd.firstChild) {
            const textSnippet = this.config.snippetModel
                .getSnippetByName("snippet_structure", "s_text_block")
                .content.cloneNode(true);
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            const container = textSnippet.querySelector(".container");
            container.replaceChildren(baseContainer);
            wrapperTd.replaceChildren(textSnippet);
            this.dependencies.selection.setSelection({
                anchorNode: baseContainer,
                anchorOffset: 0,
            });
            this.dependencies.history.addStep();
            this.dependencies.builderOptions.updateContainers(textSnippet);
            this.dependencies.disableSnippets.disableUndroppableSnippets();
        }
    }
}

registry.category("mass_mailing-plugins").add(EmptyMailingPlugin.id, EmptyMailingPlugin);
