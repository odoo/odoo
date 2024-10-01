import { isProtected } from "@html_editor/utils/dom_info";
import { Plugin } from "../plugin";
import { descendants } from "../utils/dom_traversal";

export class CommentPlugin extends Plugin {
    static name = "comment";

    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE":
                this.removeComment(payload.node);
                break;
        }
    }

    removeComment(node) {
        for (const el of [node, ...descendants(node)]) {
            if (el.nodeType === Node.COMMENT_NODE && !isProtected(el)) {
                el.remove();
                return;
            }
        }
    }
}
