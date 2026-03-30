import { Command } from "commander";

import { ForgeClient } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, info, ok, printDiff } from "../../output.js";

export function registerForgeDiffCommand(forge: Command): void {
    forge
        .command("diff")
        .description("Show diff between current state and last build")
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
                const result = await client.diff(moduleRecord.id);
                if (result.clean) {
                    console.log(ok("Nothing to build"));
                    return;
                }
                printDiff(result);
            } finally {
                console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
            }
        });
}
