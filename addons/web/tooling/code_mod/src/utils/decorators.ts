import { NodePath } from "@babel/traverse";

import { Env } from "./env";
import { isJsFile } from "./file_path";
import { getProgramPathFrom } from "./node_path";

export function toActionOnJsFile(fn: (path: NodePath | null, env: Env) => void) {
    return (env: Env) => {
        if (!isJsFile(env.filePath)) {
            return;
        }
        fn(getProgramPathFrom(env), env);
    };
}
