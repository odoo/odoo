import { Command } from "commander";
import chalk from "chalk";

import { ForgeClient } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, info, ok, warn } from "../../output.js";

function renderBlockDiff(generatedContent: string | null, currentContent: string | null): void {
    const generatedLines = (generatedContent ?? "").split("\n");
    const currentLines = (currentContent ?? "").split("\n");
    console.log(chalk.red("--- generated"));
    for (const line of generatedLines) {
        console.log(chalk.red(`- ${line}`));
    }
    console.log(chalk.green("+++ current"));
    for (const line of currentLines) {
        console.log(chalk.green(`+ ${line}`));
    }
}

export function registerForgeConflictsCommand(forge: Command): void {
    forge
        .command("conflicts")
        .description("Show export conflicts against generated blocks")
        .argument("<module>", "Module technical name")
        .action(async function (this: Command, moduleName: string) {
            const startedAt = Date.now();
            try {
                const globals = this.optsWithGlobals() as { engineUrl?: string; output?: string };
                const config = loadConfig({
                    engineUrl: globals.engineUrl,
                    outputPath: globals.output,
                });
                const client = new ForgeClient(config.engineUrl);
                const moduleRecord = await client.resolveModule(moduleName);
                const result = await client.conflicts(moduleRecord.id);
                for (const message of result.warnings) {
                    console.log(warn(message));
                }
                if (result.conflicts.length === 0) {
                    console.log(ok("No conflicts"));
                    return;
                }
                for (const conflict of result.conflicts) {
                    console.log(chalk.bold(`${conflict.file_path} [${conflict.block_id}]`));
                    renderBlockDiff(conflict.generated_content, conflict.current_content);
                }
            } finally {
                console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
            }
        });
}
