import { NodePath } from "@babel/traverse";
import { Identifier } from "@babel/types";

import { getBindingPath } from "./binding";
import { Env } from "./env";
import { normalizeSource } from "./file_path";
import { ensureProgramPath } from "./node_path";
import { ExpressionPattern } from "./pattern";

export function getLocalIdentifierOfRegistry(
    path: NodePath | null,
    env: Env,
): NodePath<Identifier> | null {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return null;
    }
    for (const p of programPath.get("body")) {
        if (!p.isImportDeclaration()) {
            continue;
        }
        const s = normalizeSource(p.node.source.value, env);
        if (s !== "@web/core/registry") {
            continue;
        }
        for (const s of p.get("specifiers")) {
            if (s.isImportSpecifier()) {
                const imported = s.get("imported");
                if (imported.isIdentifier({ name: "registry" })) {
                    return s.get("local");
                }
            }
        }
    }
    return null;
}

const viewRegistryPattern1 = new ExpressionPattern("viewRegistry");
const viewRegistryPattern2 = new ExpressionPattern("registry.category('views')");

/** heuristic */
export function isViewRegistry(path: NodePath) {
    if (!path.isExpression()) {
        return false;
    }
    if (path.isIdentifier()) {
        const valuePath = getBindingPath(path)?.get("init");
        if (!valuePath || valuePath instanceof Array) {
            return false;
        }
        if (valuePath.isExpression()) {
            return Boolean(viewRegistryPattern2.detect(valuePath));
        }
        return false;
    }
    return Boolean(viewRegistryPattern1.detect(path) || viewRegistryPattern2.detect(path));
}
