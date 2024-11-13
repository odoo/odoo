import traverse, { NodePath } from "@babel/traverse";
import {
    ClassDeclaration,
    ClassExpression,
    Declaration,
    Identifier,
    ImportDeclaration,
    isIdentifier,
    Node,
    ObjectExpression,
    Program,
} from "@babel/types";

import { getBinding, getBindingPath } from "./binding";
import { Env } from "./env";
import { getAbsolutePathFromImportDeclaration } from "./file_path";

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

export function getProgramPathFrom(env: Env) {
    const ast = env.getAST(env.filePath);
    return getProgramPath(ast);
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
            const ast = env.getAST(absolutePath);
            if (!ast) {
                return null;
            }
            const name =
                path.isImportSpecifier() && isIdentifier(path.node.imported)
                    ? path.node.imported.name
                    : null;
            let res: NodePath | null = null;
            traverse(ast, {
                Program(path) {
                    if (name) {
                        const b = path.scope.getBinding(name);
                        if (b) {
                            res = b.path;
                        }
                        path.stop();
                    }
                },
                ExportDefaultDeclaration(path) {
                    res = path.get("declaration");
                    path.stop();
                },
            });
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
