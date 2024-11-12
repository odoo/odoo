import traverse, { NodePath } from "@babel/traverse";
import * as t from "@babel/types";

import { getBinding, getBindingPath } from "../utils/binding";
import { ExtendedEnv } from "../utils/env";
import { addImports, getNormalizedNode, removeUnusedImports } from "../utils/imports";
import { ensureProgramPath, getObjectPropertyPath, getProgramPath } from "../utils/node_path";
import { DeclarationPattern, ExpressionPattern } from "../utils/pattern";
import { getLocalIdentifierOfRegistry, isViewRegistry } from "../utils/registry";
import { getAbsolutePathFromImportDeclaration, isJsFile, normalizeSource } from "../utils/utils";

// for ast descriptions see https://github.com/babel/babel/blob/master/packages/babel-parser/ast/spec.md

function getDeclarationPath(id: NodePath<t.Identifier>): NodePath<t.Declaration> | null {
    const path = getBindingPath(id);
    if (path && path.parentPath?.isDeclaration()) {
        return path.parentPath;
    }
    return null;
}

export function getDefinitionFor(
    identifier: NodePath<t.Identifier>,
    env: ExtendedEnv,
): { path: NodePath; inFilePath: string } | null {
    const binding = getBinding(identifier);
    if (!binding) {
        return null;
    }
    if (binding.kind === "module") {
        const path = binding.path;
        if (path && (path.isImportSpecifier() || path.isImportDefaultSpecifier())) {
            const parentPath = path.parentPath as NodePath<t.ImportDeclaration>;
            const absolutePath = getAbsolutePathFromImportDeclaration(parentPath, env);
            const ast = env.getAST(absolutePath);
            if (!ast) {
                return null;
            }
            const name =
                path.isImportSpecifier() && t.isIdentifier(path.node.imported)
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
            return { path: res, inFilePath: absolutePath };
        }
    }
    if (["const", "let"].includes(binding.kind)) {
        return { path: binding.path, inFilePath: env.inFilePath };
    }
    return null;
}

function getClassPropertyForProps(
    path: NodePath<t.ArrowFunctionExpression | t.FunctionExpression | t.ObjectMethod>,
    declarations: t.ImportDeclaration[],
    env: ExtendedEnv,
) {
    // remove view param
    const params = [...path.node.params];
    params.splice(1, 1);

    const body = path.get("body");

    const refs = path.scope.getBinding("view")?.referencePaths || [];
    body.traverse({
        Identifier(path) {
            if (refs.includes(path)) {
                // change view in this in body
                path.replaceWith(t.thisExpression());
            }
            const declarationPath = getDeclarationPath(path);
            if (declarationPath && declarationPath.isImportDeclaration()) {
                const declarationNode = getNormalizedNode(declarationPath, env);
                declarations.push(declarationNode);
            }
        },
    });

    // const body = path.node.body;
    const finalBody = t.isExpression(body.node)
        ? t.blockStatement([t.returnStatement(body.node)])
        : body.node;
    const id = t.identifier("getComponentProps");

    const m = t.classMethod("method", id, params, finalBody);
    m.static = true;
    return m;
}

function getClassPropertyPath(
    path: NodePath<t.ClassDeclaration | t.ClassExpression>,
    name: string,
) {
    for (const p of path.get("body").get("body")) {
        if (p.isClassProperty() && t.isIdentifier(p.node.key, { name })) {
            return p.get("value");
        }
    }
    return null;
}

function copyKeys(
    objectPath: NodePath<t.ObjectExpression>,
    targetPath: NodePath<t.ClassDeclaration | t.ClassExpression>,
    env: ExtendedEnv,
) {
    const body = targetPath.node.body.body;
    let someThingCopied = false;
    const declarations: t.ImportDeclaration[] = [];
    for (const p of objectPath.get("properties")) {
        if (p.isObjectProperty()) {
            if (!t.isIdentifier(p.node.key)) {
                continue;
            }
            if (["type", "Controller"].includes(p.node.key.name)) {
                continue;
            }
            if (p.node.key.name === "props") {
                const value = p.get("value");
                if (
                    value.isArrowFunctionExpression() ||
                    value.isFunctionExpression() ||
                    value.isObjectMethod()
                ) {
                    body.unshift(getClassPropertyForProps(value, declarations, env));
                    someThingCopied = true;
                }
                continue;
            }
            if (t.isIdentifier(p.node.key) && t.isExpression(p.node.value)) {
                const classProperty = t.classProperty(p.node.key, p.node.value);
                classProperty.static = true;
                body.unshift(classProperty);
                const value = p.get("value");
                if (value.isIdentifier()) {
                    const declarationPath = getDeclarationPath(value);
                    if (declarationPath && declarationPath.isImportDeclaration()) {
                        const declarationNode = getNormalizedNode(declarationPath, env);
                        declarations.push(declarationNode);
                    }
                }
                someThingCopied = true;
            }
        } else if (p.isObjectMethod() && t.isIdentifier(p.node.key, { name: "props" })) {
            const value = p.get("value");
            if (
                !(value instanceof Array) &&
                (value.isArrowFunctionExpression() ||
                    value.isFunctionExpression() ||
                    value.isObjectMethod())
            ) {
                body.unshift(getClassPropertyForProps(value, declarations, env));
                someThingCopied = true;
            }
        }
    }
    return { someThingCopied, declarations };
}

const addPattern2Args = new ExpressionPattern("__target.add(__key, __added)");
const addPattern3Args = new ExpressionPattern("__target.add(__key, __added, __y)");
const declarationPattern = new DeclarationPattern("const __id = __def");

function getViewDef(path: NodePath, env: ExtendedEnv): NodePath<t.ObjectExpression> | null {
    if (path.isObjectExpression()) {
        return path;
    }
    if (path.isIdentifier()) {
        const declarationPath = getDeclarationPath(path);
        if (!declarationPath) {
            return null;
        }
        const { __def: __viewDef } = declarationPattern.detect(declarationPath) || {};
        if (!__viewDef || __viewDef instanceof Array) {
            return null;
        }
        if (__viewDef.isObjectExpression()) {
            env.cleaning.add(() => declarationPath.remove());
            return __viewDef;
        }
    }
    return null;
}

function createController(
    viewDef: NodePath<t.ObjectExpression>,
    controllerValuePath: NodePath<t.Identifier>,
    env: ExtendedEnv,
) {
    const id = viewDef.scope.generateUidIdentifier("Controller");
    const newControllerDeclaration = t.classDeclaration(
        id,
        controllerValuePath.node,
        t.classBody([]),
    );
    viewDef.getStatementParent()?.insertBefore(newControllerDeclaration);
    const newControllerDeclarationPath = viewDef
        .getStatementParent()
        ?.getPrevSibling() as NodePath<t.ClassDeclaration>;
    copyKeys(viewDef, newControllerDeclarationPath, env);
    env.tagAsModified(env.inFilePath);
    return newControllerDeclarationPath.get("id") as NodePath<t.Identifier>;
}

// use recursivity

function getImportForController(id: NodePath<t.Identifier>, env: ExtendedEnv) {
    const d = getDefinitionFor(id, env);
    if (d) {
        const s = normalizeSource(d.inFilePath, { ...env, inFilePath: d.inFilePath });
        const i = t.importDeclaration([t.importSpecifier(id.node, id.node)], t.stringLiteral(s));
        return i;
    }
    return null;
}

function processView(viewDef: NodePath<t.ObjectExpression>, env: ExtendedEnv) {
    const controllerValuePath = getObjectPropertyPath(viewDef, "Controller");
    if (!controllerValuePath) {
        // view is maybe an extension
        const spreadElement = viewDef.get("properties").find((p) => p.isSpreadElement());
        if (spreadElement) {
            const arg = spreadElement.get("argument");
            if (arg.isIdentifier()) {
                const definition = getDefinitionFor(arg, env);
                let controllerValuePath: NodePath<unknown> | null = null;

                if (definition?.path && definition.path.isVariableDeclarator()) {
                    const def = definition.path.get("init");
                    if (def && def.isObjectExpression()) {
                        // we get "super" view (?)
                        controllerValuePath = getObjectPropertyPath(def, "Controller");
                    }
                } else if (definition?.path && definition.path.isClassDeclaration()) {
                    // we get "super" view (?)
                    controllerValuePath = getClassPropertyPath(definition.path, "Controller");
                }
                if (definition && controllerValuePath && controllerValuePath?.isIdentifier()) {
                    const i = getImportForController(controllerValuePath, {
                        ...env,
                        inFilePath: definition.inFilePath,
                    });
                    if (i) {
                        addImports(viewDef, [i], env);
                    }
                    return createController(viewDef, controllerValuePath, env);
                }
                return null;
            }
        }
    } else if (controllerValuePath?.isIdentifier()) {
        const definition = getDefinitionFor(controllerValuePath, env);
        if (definition && definition.path.isClassDeclaration()) {
            const { someThingCopied, declarations } = copyKeys(viewDef, definition.path, env);
            env.tagAsModified(env.inFilePath);
            if (someThingCopied && definition.inFilePath !== env.inFilePath) {
                if (declarations.length) {
                    addImports(definition.path, declarations, {
                        ...env,
                        inFilePath: definition.inFilePath,
                    });
                }
                env.tagAsModified(definition.inFilePath);
            }
            return controllerValuePath;
        }
    } else if (controllerValuePath?.isClassExpression()) {
        copyKeys(viewDef, controllerValuePath, env);
        env.tagAsModified(env.inFilePath);
        return controllerValuePath;
    }
    return null;
}

function viewObjectToController(path: NodePath | null, env: ExtendedEnv) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return null;
    }
    const localPath = getLocalIdentifierOfRegistry(programPath, env);
    if (!localPath) {
        return;
    }
    programPath.traverse({
        CallExpression(path) {
            const { __target, __added, __key } =
                addPattern2Args.detect(path) || addPattern3Args.detect(path) || {};
            if (!__target || !__added || __target instanceof Array || __added instanceof Array) {
                return;
            }
            if (!isViewRegistry(__target)) {
                return;
            }
            const viewDef = getViewDef(__added, env);
            if (viewDef && viewDef.isObjectExpression()) {
                const controllerValuePath = processView(viewDef, env);
                if (controllerValuePath) {
                    __added.replaceWith(controllerValuePath);
                    env.cleaning.add(() => removeUnusedImports(path, env));
                    return;
                }
            }
            if (__key instanceof Array) {
                return;
            }
            console.log(
                `Not changed in (${env.inFilePath}): `,
                __key.isStringLiteral() ? __key.node.value : "non identifier key",
            );
        },
    });
}

export function view_object_to_controller(env: ExtendedEnv) {
    if (!isJsFile(env.inFilePath)) {
        return;
    }
    viewObjectToController(getProgramPath(env.getAST(env.inFilePath)), env);
}
