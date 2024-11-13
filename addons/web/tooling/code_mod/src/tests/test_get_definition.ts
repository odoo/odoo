import { parse } from "@babel/parser";
import traverse from "@babel/traverse";

import { view_object_to_controller } from "../operations/view_object_to_controller";
import { Env } from "../utils/env";
import { getDefinitionFor } from "../utils/node_path";

function makeParams(fileContents: Record<string, string>): Env {
    const cacheAST = Object.fromEntries(
        Object.entries(fileContents).map(([filePath, source]) => [
            filePath,
            parse(source, { sourceType: "module" }),
        ]),
    );
    const modifiedAST = new Set();
    function getAST(filePath: string) {
        return cacheAST[filePath];
    }
    function tagAsModified(filePath: string) {
        modifiedAST.add(filePath);
    }
    const filePath = Object.keys(fileContents)[0];
    return { inFilePath: filePath, getAST, tagAsModified, cleaning: new Set() };
}

function call_get_definition(env: Env) {
    const ast = env.getAST(env.inFilePath);
    if (!ast) {
        return;
    }
    traverse(ast, {
        Identifier(path) {
            getDefinitionFor(path, env);
        },
    });
}

function call_get_definition_with(fileContents: Record<string, string>) {
    call_get_definition(makeParams(fileContents));
}

call_get_definition_with({
    "/a.js": `
        import a from "/b";
        const b = { a };
    `,
    "/b.js": `
        export default class A {};
    `,
});

view_object_to_controller(
    makeParams({
        "/a.js": `
        import { registry as r } from "@web/core/registry";
        const v = r;
        r.category("views").add("k", {});
    `,
    }),
);
