import { opendirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { Env, prepareEnv, PartialEnv } from "./env";

function IS_EXCLUDED_FOLDER(dirPath: string): boolean {
    return (
        !dirPath.endsWith("/node_modules") &&
        !dirPath.endsWith("/static/lib") &&
        !dirPath.endsWith("/.git")
    );
}

function _execute(dirPath: string, env: PartialEnv, operation: (env: Env) => void) {
    const fsDir = opendirSync(dirPath);
    let fsDirent;
    while ((fsDirent = fsDir.readSync())) {
        const direntPath = path.join(dirPath, fsDirent.name);
        if (fsDirent.isFile()) {
            debugger
            operation({ ...env, filePath: direntPath });
        } else if (fsDirent.isDirectory() && !IS_EXCLUDED_FOLDER(direntPath)) {
            _execute(direntPath, env, operation);
        }
    }
    fsDir.closeSync();
}

const SEP =
    "\n=====================================================================================================\n";
export function execute(
    operations: ((env: Env) => void)[],
    directoriesToProcess: string[],
    write = false,
) {
    const {
        modifiedFiles,
        clearCaches,
        getCode,
        getAST,
        getFileContent,
        getProgramPath,
        tagAsModified,
    } = prepareEnv();

    for (const operation of operations) {
        const cleanups: Set<() => void> = new Set();
        const env: PartialEnv = { getFileContent, getAST, getProgramPath, tagAsModified, cleanups };

        for (const dirPath of directoriesToProcess) {
            _execute(dirPath, env, operation);
        }

        for (const cleanup of cleanups) {
            cleanup();
        }

        let count = 1;
        for (const filePath in modifiedFiles) {
            const code = getCode(filePath);
            if (!code) {
                continue;
            }
            if (write) {
                writeFileSync(filePath, code);
            } else {
                console.log(SEP, `(${count}) `, filePath, SEP);
                console.log(code);
                count++;
            }
        }

        clearCaches();
    }
}
