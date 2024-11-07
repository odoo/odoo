import { NodePath } from "@babel/traverse";

import { ExtendedEnv } from "../utils/env";
import { ensureProgramPath, getProgramPath } from "../utils/node_path";
import { isJsFile } from "../utils/utils";

function putImportsOnTop(path: NodePath | null, env: ExtendedEnv) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return;
    }
    const imports = [];
    const others = [];
    for (const p of programPath.get("body")) {
        if (p.isImportDeclaration()) {
            imports.push(p.node);
        } else {
            others.push(p.node);
        }
    }
    programPath.node.body = [...imports, ...others];
    env.tagAsModified(env.inFilePath);
}

export function put_imports_on_top(env: ExtendedEnv) {
    if (!isJsFile(env.inFilePath)) {
        return;
    }
    const ast = env.getAST(env.inFilePath);
    if (!ast) {
        return;
    }
    putImportsOnTop(getProgramPath(ast), env);
}
