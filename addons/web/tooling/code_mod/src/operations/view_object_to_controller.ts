import { NodePath } from "@babel/traverse";
import * as t from "@babel/types";

import { toActionOnJsFile } from "../utils/decorators";
import { Env } from "../utils/env";
import { normalizeSource } from "../utils/file_path";
import { addImports, getNormalizedNode, removeUnusedImports } from "../utils/imports";
import {
    ensureProgramPath,
    getClassPropertyPath,
    getDeclarationPath,
    getDefinitionFor,
    getObjectPropertyPath,
} from "../utils/node_path";
import { DeclarationPattern, ExpressionPattern } from "../utils/pattern";
import { getLocalIdentifierOfRegistry, isViewRegistry } from "../utils/registry";

// for ast descriptions see https://github.com/babel/babel/blob/master/packages/babel-parser/ast/spec.md

function getClassPropertyForProps(
    path: NodePath<t.ArrowFunctionExpression | t.FunctionExpression | t.ObjectMethod>,
    declarations: t.ImportDeclaration[],
    env: Env,
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

function copyKeys(
    objectPath: NodePath<t.ObjectExpression>,
    targetPath: NodePath<t.ClassDeclaration | t.ClassExpression>,
    env: Env,
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

const declarationPattern = new DeclarationPattern("const __id = __def");

function getViewDef(path: NodePath, env: Env): NodePath<t.ObjectExpression> | null {
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
    env: Env,
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
    env.tagAsModified(env.filePath);
    return newControllerDeclarationPath.get("id") as NodePath<t.Identifier>;
}

function getImportForController(id: NodePath<t.Identifier>, env: Env) {
    const d = getDefinitionFor(id, env);
    if (d) {
        const s = normalizeSource(d.filePath, { ...env, filePath: d.filePath });
        const i = t.importDeclaration([t.importSpecifier(id.node, id.node)], t.stringLiteral(s));
        return i;
    }
    return null;
}

function processView(viewDef: NodePath<t.ObjectExpression>, env: Env) {
    const controllerValuePath = getObjectPropertyPath(viewDef, "Controller");
    if (!controllerValuePath) {
        // view is maybe an extension
        const spreadElements = viewDef.get("properties").filter((p) => p.isSpreadElement());
        if (spreadElements.length === 1) {
            const arg = spreadElements[0].get("argument");
            if (arg.isIdentifier()) {
                const definition = getDefinitionFor(arg, env);
                if (definition?.path && definition.filePath !== env.filePath) {
                    view_object_to_controller({ ...env, filePath: definition.filePath });
                }
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
                        filePath: definition.filePath,
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
            env.tagAsModified(env.filePath);
            if (someThingCopied && definition.filePath !== env.filePath) {
                if (declarations.length) {
                    addImports(definition.path, declarations, {
                        ...env,
                        filePath: definition.filePath,
                    });
                }
                env.tagAsModified(definition.filePath);
            }
            return controllerValuePath;
        }
    } else if (controllerValuePath?.isClassExpression()) {
        copyKeys(viewDef, controllerValuePath, env);
        env.tagAsModified(env.filePath);
        return controllerValuePath;
    }
    return null;
}

function processViewPath(viewPath: NodePath, env: Env) {
    const viewDef = getViewDef(viewPath, env);
    if (viewDef?.isClassDeclaration || viewDef?.isClassExpression) {
        return true;
    }
    if (viewDef?.isObjectExpression()) {
        const controllerValuePath = processView(viewDef, env);
        if (controllerValuePath) {
            viewPath.replaceWith(controllerValuePath);
            return true;
        }
    }
    return false;
}

const addPattern2Args = new ExpressionPattern("__target.add(__key, __added)");
const addPattern3Args = new ExpressionPattern("__target.add(__key, __added, __y)");
function getViewRegistryElementPaths(path: NodePath | null, env: Env) {
    const programPath = ensureProgramPath(path);
    if (!programPath) {
        return [];
    }
    const localPath = getLocalIdentifierOfRegistry(programPath, env);
    if (!localPath) {
        return [];
    }
    const viewPaths: NodePath[] = [];
    programPath.traverse({
        CallExpression(path) {
            const { __target, __added } =
                addPattern2Args.detect(path) || addPattern3Args.detect(path) || {};
            if (!__target || !__added || __target instanceof Array || __added instanceof Array) {
                return;
            }
            if (!isViewRegistry(__target)) {
                return;
            }
            viewPaths.push(__added);
        },
    });
    return viewPaths;
}

function viewObjectToController(path: NodePath | null, env: Env): void {
    const viewPaths = getViewRegistryElementPaths(path, env);
    let logUnprocessed = false;
    for (const viewPath of viewPaths) {
        const sucess = processViewPath(viewPath, env);
        if (!sucess) {
            logUnprocessed = true;
        }
    }
    env.cleaning.add(() => removeUnusedImports(path, env));
    if (logUnprocessed) {
        console.log(`Unprocessed views in ${env.filePath}`);
    }
}

export const view_object_to_controller = toActionOnJsFile(viewObjectToController);
