import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export interface Config {
    engineUrl: string;
    outputPath?: string;
}

export type ConfigFlags = Partial<Config>;

const DEFAULT_ENGINE_URL = "http://localhost:8765";

function normalizeUrl(url: string): string {
    return url.replace(/\/+$/, "");
}

function findProjectConfig(startDir: string): string | null {
    let currentDir = path.resolve(startDir);
    while (true) {
        const candidate = path.join(currentDir, ".kodoo.json");
        if (existsSync(candidate)) {
            return candidate;
        }
        const parentDir = path.dirname(currentDir);
        if (parentDir === currentDir) {
            return null;
        }
        currentDir = parentDir;
    }
}

function loadFileConfig(startDir: string): ConfigFlags {
    const configPath = findProjectConfig(startDir);
    if (!configPath) {
        return {};
    }
    try {
        const raw = readFileSync(configPath, "utf-8");
        const parsed = JSON.parse(raw) as ConfigFlags;
        return parsed;
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        throw new Error(`Failed to read ${configPath}: ${message}`);
    }
}

export function loadConfig(flags: ConfigFlags): Config {
    const fileConfig = loadFileConfig(process.cwd());
    const engineUrl =
        flags.engineUrl ||
        process.env.KODOO_ENGINE_URL ||
        fileConfig.engineUrl ||
        DEFAULT_ENGINE_URL;
    const outputPath =
        flags.outputPath ||
        process.env.KODOO_OUTPUT_PATH ||
        fileConfig.outputPath;
    return {
        engineUrl: normalizeUrl(engineUrl),
        outputPath,
    };
}
