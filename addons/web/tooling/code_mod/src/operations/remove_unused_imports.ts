import { NodePath } from "@babel/traverse";

import { ExtendedEnv } from "../utils/env";
import { ensureProgramPath, getProgramPath } from "../utils/node_path";
import { isJsFile } from "../utils/utils";

function removeUnusedImports(path: NodePath | null, env: ExtendedEnv) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return;
    }
    const usedSpecifiers = new Set();
    programPath.traverse({
        ImportDeclaration: (p) => {
            p.skip();
        },
        Identifier: (p) => {
            const path = p.scope.getBinding(p.node.name)?.path || null;
            if (
                path &&
                (path.isImportSpecifier() ||
                    path.isImportDefaultSpecifier() ||
                    path.isImportNamespaceSpecifier())
            ) {
                usedSpecifiers.add(path.node.local.name);
            }
        },
    });
    programPath.traverse({
        ImportDeclaration: (path) => {
            let hasRemovedSomething = false;
            for (const s of path.get("specifiers")) {
                const name = s.node.local.name;
                if (!usedSpecifiers.has(name)) {
                    hasRemovedSomething = true;
                    s.remove();
                    env.tagAsModified(env.inFilePath);
                }
            }
            if (hasRemovedSomething && !path.node.specifiers.length) {
                path.remove();
                env.tagAsModified(env.inFilePath);
            }
        },
    });
}

export function remove_unused_imports(env: ExtendedEnv) {
    if (!isJsFile(env.inFilePath)) {
        return;
    }
    const ast = env.getAST(env.inFilePath);
    if (!ast) {
        return;
    }
    removeUnusedImports(getProgramPath(ast), env);
}
