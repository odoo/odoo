import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DisableSnippetsPlugin extends Plugin {
    static id = "disableSnippets";
    static shared = ["disableUndroppableSnippets"];

    disableUndroppableSnippets() {}
}

registry.category("translation-plugins").add(DisableSnippetsPlugin.id, DisableSnippetsPlugin);
