import { readFileSync } from "node:fs";

import { parse as babelParser } from "@babel/parser";
import traverse, { NodePath } from "@babel/traverse";
import { File, Program } from "@babel/types";
import { parse, print } from "recast"; // https://github.com/benjamn/recast

export interface Env extends PartialEnv {
    filePath: string;
}

export interface PartialEnv {
    getFileContent: (filePath: string) => string | null;
    getAST: (filePath: string) => File | null;
    getProgramPath: (filePath: string) => NodePath<Program> | null;

    tagAsModified: (filePath: string) => void;
    cleanups: Set<() => void>;
}

const parser = {
    parse(data: string) {
        return babelParser(data, { sourceType: "module" });
    },
};

export function defaultMakeGetFileContent() {
    const cacheFileContent: Map<string, string> = new Map();
    function getFileContent(filePath: string) {
        if (!cacheFileContent.has(filePath)) {
            let content;
            try {
                content = readFileSync(filePath, { encoding: "utf-8" });
            } catch {
                console.log(`(getFileContent) Unable to read ${filePath}`);
            }
            if (typeof content === "string") {
                cacheFileContent.set(filePath, content);
            }
        }
        return cacheFileContent.get(filePath) || null;
    }
    return {
        cacheFileContent,
        getFileContent,
    };
}

export function prepareEnv(
    makeGetFileContent: () => {
        cacheFileContent: Map<string, string>;
        getFileContent: (filePath: string) => string | null;
    } = defaultMakeGetFileContent,
) {
    const modified: Set<string> = new Set();

    const { cacheFileContent, getFileContent } = makeGetFileContent();

    const cacheAST: Map<string, File> = new Map();
    const cacheProgramPath: Map<string, NodePath<Program>> = new Map();

    function getAST(filePath: string): File | null {
        if (!cacheAST.has(filePath)) {
            const fileContent = getFileContent(filePath);
            if (!fileContent) {
                return null;
            }
            let ast;
            try {
                ast = parse(fileContent, { parser });
            } catch {
                console.log(`(getAST) Unable to parse ${filePath}`);
            }
            if (ast) {
                cacheAST.set(filePath, ast);
            }
        }
        return cacheAST.get(filePath) || null;
    }

    function getProgramPath(filePath: string): NodePath<Program> | null {
        if (!cacheProgramPath.has(filePath)) {
            const ast = getAST(filePath);
            if (!ast) {
                return null;
            }
            let programPath = null;
            try {
                traverse(ast, {
                    Program(path) {
                        programPath = path;
                        path.stop();
                    },
                });
            } catch {
                console.log(`(getProgramPath) Unable to traverse ast for ${filePath}`);
            }
            if (programPath) {
                cacheProgramPath.set(filePath, programPath);
            }
        }
        return cacheProgramPath.get(filePath) || null;
    }

    function* modifiedFiles() {
        for (const filePath of modified) {
            yield filePath;
        }
    }

    return {
        clearCaches() {
            cacheFileContent.clear();
            cacheAST.clear();
            cacheProgramPath.clear();
            modified.clear();
        },
        getCode(filePath: string): string | null {
            const ast = cacheAST.get(filePath);
            if (ast) {
                try {
                    const printResult = print(ast);
                    return printResult.code;
                } catch {
                    console.log(`Unable to print ast code for ${filePath}`);
                }
            }
            return null;
        },
        getFileContent,
        getAST,
        getProgramPath,
        tagAsModified(...filePaths: string[]) {
            for (const filePath of filePaths) {
                modified.add(filePath);
            }
        },
        modifiedFiles,
    };
}
