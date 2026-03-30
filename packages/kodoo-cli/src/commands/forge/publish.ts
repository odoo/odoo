import { Command } from "commander";
import Enquirer from "enquirer";
import ora from "ora";

import { ForgeClient, type PublishMode } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, err, info, ok, printDiff } from "../../output.js";

export function registerForgePublishCommand(forge: Command): void {
    forge
        .command("publish")
        .description("Publish a forge module")
        .argument("<module>", "Module technical name")
        .requiredOption("--mode <mode>", "Publish mode: runtime, export, or both")
        .option("--yes", "Skip confirmation prompt")
        .action(
            async function (
                this: Command,
                moduleName: string,
                options: { mode: PublishMode; yes?: boolean },
            ) {
                const startedAt = Date.now();
                try {
                    const globals = this.optsWithGlobals() as { engineUrl?: string; output?: string };
                    const config = loadConfig({
                        engineUrl: globals.engineUrl,
                        outputPath: globals.output,
                    });
                    const client = new ForgeClient(config.engineUrl);
                    const moduleRecord = await client.resolveModule(moduleName);
                    const diff = await client.diff(moduleRecord.id);
                    printDiff(diff);
                    if (!options.yes) {
                        const answer = await Enquirer.prompt<{ confirm: boolean }>({
                            type: "confirm",
                            name: "confirm",
                            message: `Publish module '${moduleRecord.technical_name}' with mode '${options.mode}'?`,
                            initial: false,
                        });
                        if (!answer.confirm) {
                            console.log(info("Publish cancelled"));
                            return;
                        }
                    }
                    const spinner = ora({
                        text: `Publishing ${moduleRecord.technical_name}`,
                        isEnabled: process.stderr.isTTY,
                    }).start();
                    const result = await client.publish(moduleRecord.id, options.mode);
                    spinner.stop();
                    console.log(ok(`Published ${moduleRecord.technical_name}`));
                    for (const filePath of result.applied) {
                        console.log(`  ${filePath}`);
                    }
                    if (result.errors.length > 0) {
                        for (const message of result.errors) {
                            console.error(err(message));
                        }
                        process.exitCode = 1;
                    }
                } finally {
                    console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
                }
            },
        );
}
