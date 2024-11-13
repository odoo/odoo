import { NodePath } from "@babel/traverse";

import { Env } from "./env";
import { isJsFile } from "./utils";
import { getProgramPathFrom } from "./node_path";

export function actionOnJsFile(fn: (path: NodePath | null, env: Env) => void) {
    return (env: Env) => {
        if (!isJsFile(env.filePath)) {
            return;
        }
        fn(getProgramPathFrom(env), env);
    };
}
