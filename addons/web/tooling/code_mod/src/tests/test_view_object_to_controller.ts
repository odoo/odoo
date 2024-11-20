import { view_object_to_controller } from "../operations/view_object_to_controller";
import { Env, prepareEnv, PartialEnv } from "../utils/env";

function makePartialEnv(cacheFileContent: Map<string, string>): PartialEnv {
    function makeGetFileContent() {
        return {
            cacheFileContent,
            getFileContent(filePath: string) {
                return cacheFileContent.get(filePath) || null;
            },
        };
    }
    const { getAST, getFileContent, getProgramPath, tagAsModified } =
        prepareEnv(makeGetFileContent);
    const cleanups: Set<() => void> = new Set();
    return { getFileContent, getAST, getProgramPath, tagAsModified, cleanups };
}

function makeEnv(filePath: string, cacheFileContent: Map<string, string>): Env {
    return { ...makePartialEnv(cacheFileContent), filePath };
}

const cacheFileContent = new Map([
    [
        "/a.js",
        `
            import { registry as r } from "@web/core/registry";
            const v = r;
            r.category("views").add("k", {});
        `,
    ],
]);

const env = makeEnv("/a.js", cacheFileContent);

view_object_to_controller(env);
