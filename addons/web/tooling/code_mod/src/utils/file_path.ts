import { statSync } from "node:fs";
import path from "node:path";

import { NodePath } from "@babel/traverse";
import { ImportDeclaration } from "@babel/types";

import { Env } from "./env";

export function isJsFile(filePath: string) {
    return path.extname(filePath) === ".js";
}

export type AbsolutPath = string; // of the form /a/b/c.js (normalized)
export type OdooPath = string; // of the form @web/a/b/c (normalized)

export const ODOO_PATH = "/home/odoo/src/odoo/";
export const ENTERPRISE_PATH = "/home/odoo/src/enterprise/";

const regex = /@(\w+)(\/.*)/;
export function toAbsolutePath(odooPath: string, env: Env) {
    const match = odooPath.match(regex);
    if (match) {
        const [, addonName, tail] = match;
        let prefix;
        try {
            const p = path.join(ODOO_PATH, "addons", addonName);
            const s = statSync(p);
            if (s.isDirectory()) {
                prefix = p;
            }
        } catch {
            try {
                const p = path.join(ENTERPRISE_PATH, addonName);
                const s = statSync(p);
                if (s.isDirectory()) {
                    prefix = p;
                }
            } catch {
                // wrong odooPath?
            }
        }
        if (prefix) {
            return path.normalize(path.join(prefix, "/static/src/", tail));
        }
    }
    const dirname = path.dirname(env.filePath);
    return path.resolve(dirname, odooPath);
}

export function getAbsolutePathFromImportDeclaration(
    declarationPath: NodePath<ImportDeclaration>,
    env: Env,
): string {
    let absolutePath = toAbsolutePath(declarationPath.node.source.value, env);
    if (!absolutePath.endsWith(".js")) {
        absolutePath += ".js";
    }
    return absolutePath;
}

// TO IMPROVE
export function normalizeSource(source: string, env: Env) {
    if (source.startsWith("@")) {
        return source;
    }
    const dir = path.dirname(env.filePath);
    source = path.resolve(dir, source);
    const p = path.join(ODOO_PATH, "addons/");
    if (source.startsWith(p)) {
        source = source.replace(p, "@").replace("/static/src/", "/");
    } else if (source.startsWith(ENTERPRISE_PATH)) {
        source = source.replace(ENTERPRISE_PATH, "@").replace("/static/src/", "/");
    }
    return source;
}
