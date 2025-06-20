import { Plugin } from "@html_editor/plugin";

export class DisableSnippetsPlugin extends Plugin {
    static id = "disableSnippets";
    static shared = ["disableUndroppableSnippets"];

    disableUndroppableSnippets() {}
}
