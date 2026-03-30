import { Command } from "commander";

import { ForgeClient } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, info, ok } from "../../output.js";

function defaultSnapshotName(): string {
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    return `snapshot-${stamp}`;
}

export function registerForgeSnapshotCommand(forge: Command): void {
    forge
        .command("snapshot")
        .description("Create a snapshot for a forge module")
        .argument("<module>", "Module technical name")
        .option("--name <name>", "Snapshot name")
        .action(async function (this: Command, moduleName: string, options: { name?: string }) {
            const startedAt = Date.now();
            try {
                const globals = this.optsWithGlobals() as { engineUrl?: string; output?: string };
                const config = loadConfig({
                    engineUrl: globals.engineUrl,
                    outputPath: globals.output,
                });
                const client = new ForgeClient(config.engineUrl);
                const moduleRecord = await client.resolveModule(moduleName);
                const snapshotName = options.name || defaultSnapshotName();
                const result = await client.snapshot(moduleRecord.id, snapshotName);
                console.log(ok(`Snapshot '${result.name}' created (id: ${result.snapshot_id})`));
            } finally {
                console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
            }
        });
}
