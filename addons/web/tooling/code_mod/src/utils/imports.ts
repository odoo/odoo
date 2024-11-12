import { NodePath } from "@babel/traverse";
import { cloneNode, ImportDeclaration, Program } from "@babel/types";

import { ExtendedEnv } from "./env";
import { ensureProgramPath, getProgramPath, getProgramPathFrom } from "./node_path";
import { areEquivalentUpToHole } from "./pattern";
import { isJsFile, normalizeSource } from "./utils";

function addImport(programPath: NodePath<Program>, imp: ImportDeclaration, env: ExtendedEnv) {
    const source = normalizeSource(imp.source.value, env);
    for (const p of programPath.get("body")) {
        if (!p.isImportDeclaration()) {
            continue;
        }
        const pSource = normalizeSource(p.node.source.value, env);
        if (source !== pSource) {
            continue;
        }
        for (const specifier of imp.specifiers) {
            if (p.node.specifiers.some((s) => areEquivalentUpToHole(specifier, s))) {
                continue;
            }
            p.node.specifiers.push(specifier);
        }
        return;
    }
    programPath.node.body.unshift(imp);
}

export function addImports(path: NodePath | null, imports: ImportDeclaration[], env: ExtendedEnv) {
    if (!imports.length) {
        return;
    }
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return;
    }
    for (const imp of imports) {
        addImport(programPath, imp, env);
    }
    env.tagAsModified(env.inFilePath);
}

export function getNormalizedNode(declarationPath: NodePath<ImportDeclaration>, env: ExtendedEnv) {
    const n = cloneNode(declarationPath.node);
    n.source.value = normalizeSource(n.source.value, env);
    return n;
}

export function normalizeImport(declarationPath: NodePath<ImportDeclaration>, env: ExtendedEnv) {
    const s = normalizeSource(declarationPath.node.source.value, env);
    if (s !== declarationPath.node.source.value) {
        declarationPath.node.source.value = s;
        env.tagAsModified(env.inFilePath);
    }
}

export function normalizeImports(path: NodePath | null, env: ExtendedEnv) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return;
    }
    programPath.traverse({
        ImportDeclaration(path) {
            normalizeImport(path, env);
            path.skip();
        },
    });
}

export function removeUnusedImports(path: NodePath | null, env: ExtendedEnv) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return;
    }
    const usedSpecifiers = new Set();
    programPath.traverse({
        ImportDeclaration(p) {
            p.skip();
        },
        Identifier(p) {
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
        ImportDeclaration(path) {
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

export function groupImports(path: NodePath | null, env: ExtendedEnv) {
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
    putImportsOnTop(getProgramPathFrom(env), env);
}

export function group_imports(env: ExtendedEnv) {
    if (!isJsFile(env.inFilePath)) {
        return;
    }
    groupImports(getProgramPathFrom(env), env);
}

export function remove_unused_imports(env: ExtendedEnv) {
    if (!isJsFile(env.inFilePath)) {
        return;
    }
    removeUnusedImports(getProgramPathFrom(env), env);
}
