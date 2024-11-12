import { writeFileSync } from "fs";

import { ExtendedEnv } from "../utils/env";
import { getFileContent, isJsFile } from "../utils/utils";

export function removeOdooModuleCommentFromFileContent(fileContent: string) {
    const match = fileContent.match(/^(\n*[^\n]+@odoo-module([^\n]+)\n+)/); // improve regex
    if (!match || ["ignore", "alias", "default"].some((t) => match[2].includes(t))) {
        return { fileContent, changed: false };
    }
    return { fileContent: fileContent.slice(match[1].length), changed: true };
}

export function remove_odoo_module_comment(env: ExtendedEnv) {
    const { inFilePath: filePath } = env;
    if (!isJsFile(filePath)) {
        return;
    }
    if (!(filePath.includes("/static/src/") || filePath.includes("/static/tests/"))) {
        return;
    }
    const fileContent = getFileContent(filePath);
    if (!fileContent) {
        return;
    }
    const { fileContent: result, changed } = removeOdooModuleCommentFromFileContent(fileContent);
    if (changed) {
        writeFileSync(filePath, result);
    }
}
