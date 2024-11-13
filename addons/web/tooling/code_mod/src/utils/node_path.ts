import { NodePath } from "@babel/traverse";
import {
    ClassDeclaration,
    ClassExpression,
    Declaration,
    Identifier,
    ImportDeclaration,
    isIdentifier,
    ObjectExpression,
    Program,
} from "@babel/types";

import { getBinding, getBindingPath } from "./binding";
import { Env } from "./env";
import { getAbsolutePathFromImportDeclaration } from "./file_path";

export function ensureProgramPath(path: NodePath | null): NodePath<Program> | null {
    if (!path) {
        return null;
    }
    if (path.isProgram()) {
        return path;
    }
    return path.findParent((p) => p.isProgram()) as NodePath<Program> | null;
}

export function getObjectPropertyPath(path: NodePath<ObjectExpression> | null, name: string) {
    if (!path) {
        return null;
    }
    for (const p of path.get("properties")) {
        if (p.isObjectProperty() && isIdentifier(p.node.key, { name })) {
            return p.get("value");
        }
    }
    return null;
}

export function getClassPropertyPath(
    path: NodePath<ClassDeclaration | ClassExpression>,
    name: string,
) {
    for (const p of path.get("body").get("body")) {
        if (p.isClassProperty() && isIdentifier(p.node.key, { name })) {
            return p.get("value");
        }
    }
    return null;
}

export function getDeclarationPath(id: NodePath<Identifier>): NodePath<Declaration> | null {
    const path = getBindingPath(id);
    if (path && path.parentPath?.isDeclaration()) {
        return path.parentPath;
    }
    return null;
}

export function getDefinitionFor(
    identifier: NodePath<Identifier>,
    env: Env,
): { path: NodePath; filePath: string } | null {
    const binding = getBinding(identifier);
    if (!binding) {
        return null;
    }
    if (binding.kind === "module") {
        const path = binding.path;
        if (path && (path.isImportSpecifier() || path.isImportDefaultSpecifier())) {
            const parentPath = path.parentPath as NodePath<ImportDeclaration>;
            const absolutePath = getAbsolutePathFromImportDeclaration(parentPath, env);
            const programPath = env.getProgramPath(absolutePath);
            if (!programPath) {
                return null;
            }
            const name =
                path.isImportSpecifier() && isIdentifier(path.node.imported)
                    ? path.node.imported.name
                    : null;
            let res: NodePath | null = null;

            if (name) {
                const b = programPath.scope.getBinding(name);
                if (b) {
                    res = b.path;
                }
            } else {
                programPath.traverse({
                    ExportDefaultDeclaration(path) {
                        res = path.get("declaration");
                        path.stop();
                    },
                });
            }
            if (!res) {
                return null;
            }
            return { path: res, filePath: absolutePath };
        }
    }
    if (["const", "let"].includes(binding.kind)) {
        return { path: binding.path, filePath: env.filePath };
    }
    return null;
}
