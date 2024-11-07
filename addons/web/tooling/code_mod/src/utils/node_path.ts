import traverse, { NodePath } from "@babel/traverse";
import { Node, Program } from "@babel/types";

export function getPath(ast: Node | null): NodePath | null {
    if (!ast) {
        return null;
    }
    let path = null;
    try {
        traverse(ast, {
            enter(p) {
                path = p;
                path.stop();
            },
        });
    } catch {
        console.log("(getPath) Unable to traverse ast");
    }
    return path;
}

export function ensureProgramPath(path: NodePath | null): NodePath<Program> | null {
    if (!path) {
        return null;
    }
    if (path.isProgram()) {
        return path;
    }
    return path.findParent((p) => p.isProgram()) as NodePath<Program> | null;
}

export function getProgramPath(ast: Node | null): NodePath<Program> | null {
    return ensureProgramPath(getPath(ast));
}
