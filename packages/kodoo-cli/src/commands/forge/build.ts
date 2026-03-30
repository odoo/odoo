import { setTimeout as delay } from "node:timers/promises";

import { Command } from "commander";
import ora from "ora";

import { ForgeClient, ForgeClientError, type BuildResponse, type ConflictsResponse } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, err, info, ok, printValidationErrors, warn } from "../../output.js";

function printBuildFiles(result: BuildResponse): void {
    console.log(ok(`Build ${result.build_id} completed`));
    for (const file of result.files) {
        const suffix = file.size_bytes !== undefined ? ` (${file.size_bytes} bytes)` : "";
        console.log(`  ${file.path}${suffix}`);
    }
}

function printConflictDetails(conflicts: ConflictsResponse): void {
    for (const warningMessage of conflicts.warnings) {
        console.log(warn(warningMessage));
    }
    for (const conflict of conflicts.conflicts) {
        console.log(warn(`${conflict.file_path} [${conflict.block_id}]`));
    }
}

async function runBuild(
    client: ForgeClient,
    moduleId: number,
    moduleName: string,
): Promise<boolean> {
    const spinner = ora({
        text: `Building ${moduleName}`,
        isEnabled: process.stderr.isTTY,
    }).start();
    try {
        const result = await client.build(moduleId);
        spinner.stop();
        printBuildFiles(result);
        return true;
    } catch (error) {
        spinner.stop();
        if (error instanceof ForgeClientError && error.status === 422) {
            const detail = error.detail as { errors?: unknown };
            if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
                printValidationErrors(detail.errors as {
                    rule: string;
                    entity: string;
                    message: string;
                }[]);
            }
            console.error(err(error.message));
            return false;
        }
        if (error instanceof ForgeClientError && error.status === 409) {
            console.error(warn(error.message));
            try {
                const conflicts = await client.conflicts(moduleId);
                printConflictDetails(conflicts);
            } catch (conflictError) {
                if (conflictError instanceof Error) {
                    console.error(warn(conflictError.message));
                }
            }
            return false;
        }
        throw error;
    }
}

export function registerForgeBuildCommand(forge: Command): void {
    forge
        .command("build")
        .description("Build a forge module")
        .argument("<module>", "Module technical name")
        .option("--watch", "Watch for changes and rebuild automatically")
        .action(async function (this: Command, moduleName: string, options: { watch?: boolean }) {
            const startedAt = Date.now();
            try {
                const globals = this.optsWithGlobals() as { engineUrl?: string; output?: string };
                const config = loadConfig({
                    engineUrl: globals.engineUrl,
                    outputPath: globals.output,
                });
                const client = new ForgeClient(config.engineUrl);
                const moduleRecord = await client.resolveModule(moduleName);
                const initialSuccess = await runBuild(client, moduleRecord.id, moduleRecord.technical_name);
                if (!initialSuccess) {
                    process.exitCode = 1;
                    return;
                }
                if (!options.watch) {
                    return;
                }
                console.log(info("Watching for changes every 5s. Press Ctrl+C to stop."));
                let stopped = false;
                const stopWatching = (): void => {
                    stopped = true;
                };
                process.once("SIGINT", stopWatching);
                try {
                    while (!stopped) {
                        await delay(5000);
                        if (stopped) {
                            break;
                        }
                        const diff = await client.diff(moduleRecord.id);
                        if (diff.clean) {
                            continue;
                        }
                        console.log(info("Changes detected, rebuilding..."));
                        const rebuildSuccess = await runBuild(
                            client,
                            moduleRecord.id,
                            moduleRecord.technical_name,
                        );
                        if (!rebuildSuccess) {
                            process.exitCode = 1;
                            break;
                        }
                    }
                } finally {
                    process.removeListener("SIGINT", stopWatching);
                }
            } finally {
                console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
            }
        });
}
