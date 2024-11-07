import { parse } from "@babel/parser";
import traverse from "@babel/traverse";

import {
    getDefinitionFor,
    view_object_to_controller,
} from "../operations/view_object_to_controller";
import { ExtendedEnv } from "../utils/env";

function makeParams(fileContents: Record<string, string>): ExtendedEnv {
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

function get_definition(env: ExtendedEnv) {
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
    get_definition(makeParams(fileContents));
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
