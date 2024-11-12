import { NodePath } from "@babel/traverse";
import { ImportDeclaration } from "@babel/types";

import { Env, ExtendedEnv } from "../utils/env";
import { ensureProgramPath, getProgramPath } from "../utils/node_path";
import { areEquivalentUpToHole } from "../utils/pattern";
import { isJsFile, normalizeSource } from "../utils/utils";

function groupImports(path: NodePath | null, env: ExtendedEnv) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return;
    }
    const importDeclarations: Record<string, NodePath<ImportDeclaration>> = {};
    for (const i of programPath.get("body")) {
        if (!i.isImportDeclaration()) {
            continue;
        }
        const sourceName = normalizeSource(i.node.source.value, env);
        if (!importDeclarations[sourceName]) {
            if (sourceName !== i.node.source.value) {
                i.node.source.value = sourceName;
                env.tagAsModified(env.inFilePath);
            }
            importDeclarations[sourceName] = i;
            continue;
        }
        for (const s of i.get("specifiers")) {
            if (
                importDeclarations[sourceName]
                    .get("specifiers")
                    .some((specifier) => areEquivalentUpToHole(specifier.node, s.node))
            ) {
                continue;
            }
            importDeclarations[sourceName].node.specifiers.push(s.node);
        }
        i.remove();
        env.tagAsModified(env.inFilePath);
    }
}

export function group_imports(filePath: string, env: Env) {
    if (!isJsFile(filePath)) {
        return;
    }
    const ast = env.getAST(filePath);
    if (!ast) {
        return;
    }
    console.log("(group_imports) Processing ", filePath);
    groupImports(getProgramPath(ast), { ...env, inFilePath: filePath });
}
