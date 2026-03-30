import { Command } from "commander";

import { ForgeClient } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, err, info, ok, printValidationErrors } from "../../output.js";

export function registerForgeValidateCommand(forge: Command): void {
    forge
        .command("validate")
        .description("Validate a forge module")
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
                const result = await client.validate(moduleRecord.id);
                if (result.valid) {
                    console.log(ok("Module is valid"));
                    return;
                }
                printValidationErrors(result.errors);
                console.error(err("Module is invalid"));
                process.exitCode = 1;
            } finally {
                console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
            }
        });
}
