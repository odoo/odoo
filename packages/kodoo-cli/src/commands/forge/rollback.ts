import { Command } from "commander";
import Enquirer from "enquirer";

import { ForgeClient, type SnapshotRecord } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, info, ok } from "../../output.js";

function formatSnapshot(snapshot: SnapshotRecord): string {
    const createdAt = snapshot.created_at ?? "-";
    const createdBy = snapshot.created_by ?? "-";
    return `${snapshot.id} | ${snapshot.name} | ${createdAt} | ${createdBy}`;
}

export function registerForgeRollbackCommand(forge: Command): void {
    forge
        .command("rollback")
        .description("Rollback a forge module to a snapshot")
        .argument("<module>", "Module technical name")
        .argument("[snapshot_id]", "Snapshot ID")
        .action(
            async function (
                this: Command,
                moduleName: string,
                snapshotIdValue: string | undefined,
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
                    const snapshots = await client.listSnapshots(moduleRecord.id);
                    if (snapshots.length === 0) {
                        throw new Error(`No snapshots found for module '${moduleRecord.technical_name}'.`);
                    }
                    let snapshot: SnapshotRecord | undefined;
                    if (snapshotIdValue) {
                        const snapshotId = Number(snapshotIdValue);
                        snapshot = snapshots.find((candidate) => candidate.id === snapshotId);
                        if (!snapshot) {
                            throw new Error(`Snapshot '${snapshotIdValue}' was not found for this module.`);
                        }
                    } else {
                        const answer = await Enquirer.prompt<{ snapshot: string }>({
                            type: "select",
                            name: "snapshot",
                            message: `Choose a snapshot for '${moduleRecord.technical_name}'`,
                            choices: snapshots.map((candidate) => ({
                                name: String(candidate.id),
                                message: formatSnapshot(candidate),
                                value: String(candidate.id),
                            })),
                        });
                        snapshot = snapshots.find(
                            (candidate) => String(candidate.id) === answer.snapshot,
                        );
                    }
                    if (!snapshot) {
                        throw new Error("Unable to resolve snapshot.");
                    }
                    const answer = await Enquirer.prompt<{ confirm: boolean }>({
                        type: "confirm",
                        name: "confirm",
                        message: `Rollback module '${moduleRecord.technical_name}' to '${snapshot.name}'?`,
                        initial: false,
                    });
                    if (!answer.confirm) {
                        console.log(info("Rollback cancelled"));
                        return;
                    }
                    await client.rollback(moduleRecord.id, snapshot.id);
                    console.log(ok(`Rolled back to '${snapshot.name}'`));
                } finally {
                    console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
                }
            },
        );
}
