import { Plugin } from "@html_editor/plugin";

export class CodePlugin extends Plugin {
    static id = "code";
    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_namespace_providers: [
            (targetedNodes, editableSelection) => {
                if (editableSelection.isCollapsed) {
                    return;
                }
                if (
                    targetedNodes.length &&
                    targetedNodes.every(
                        // All nodes should be inside a <pre>
                        (node) => node.closest?.("pre") || node.parentElement.closest("pre")
                    )
                ) {
                    return "codecompact";
                }
            },
        ],
        toolbar_groups: [
            {
                isPatch: true,
                id: "font",
                getNamespaces: (button) => {
                    if ("font-family" === button.id) {
                        return [];
                    }
                    return ["codecompact", "codeexpanded"];
                },
            },
            {
                isPatch: true,
                id: "decoration",
                getNamespaces: (button) => {
                    if (["forecolor", "backcolor", "remove_format"].includes(button.id)) {
                        return [];
                    }
                    return ["codecompact", "codeexpanded"];
                },
            },
            { isPatch: true, id: "link", namespaces: ["codecompact", "codeexpanded"] },
            { isPatch: true, id: "expand_toolbar", namespaces: ["codecompact"] },
            { isPatch: true, id: "ai", namespaces: ["codeexpanded"] },
        ],
    };
}
