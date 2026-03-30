#!/usr/bin/env node

import { Command } from "commander";

import { registerForgeBuildCommand } from "./commands/forge/build.js";
import { registerForgeConflictsCommand } from "./commands/forge/conflicts.js";
import { registerForgeDiffCommand } from "./commands/forge/diff.js";
import { registerForgeListCommand } from "./commands/forge/list.js";
import { registerForgePublishCommand } from "./commands/forge/publish.js";
import { registerForgeRollbackCommand } from "./commands/forge/rollback.js";
import { registerForgeSnapshotCommand } from "./commands/forge/snapshot.js";
import { registerForgeValidateCommand } from "./commands/forge/validate.js";
import { ForgeClientError } from "./client.js";
import { err } from "./output.js";

async function main(): Promise<void> {
    const program = new Command();
    program
        .name("kodoo")
        .description("Kodoo CLI")
        .option("--engine-url <url>", "Forge engine base URL")
        .option("--output <path>", "Output path override");

    const forge = program.command("forge").description("Forge commands");
    registerForgeListCommand(forge);
    registerForgeValidateCommand(forge);
    registerForgeBuildCommand(forge);
    registerForgeDiffCommand(forge);
    registerForgePublishCommand(forge);
    registerForgeSnapshotCommand(forge);
    registerForgeRollbackCommand(forge);
    registerForgeConflictsCommand(forge);

    await program.parseAsync(process.argv);
}

main().catch((error: unknown) => {
    if (error instanceof ForgeClientError) {
        console.error(err(error.message));
        process.exit(1);
    }
    if (error instanceof Error) {
        console.error(err(error.message));
        process.exit(1);
    }
    console.error(err(String(error)));
    process.exit(1);
});
