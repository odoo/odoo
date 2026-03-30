import { Command } from "commander";

import { ForgeClient } from "../../client.js";
import { loadConfig } from "../../config.js";
import { elapsed, info, ok, warn } from "../../output.js";

function tableRow(columns: string[], widths: number[]): string {
    return columns
        .map((column, index) => column.padEnd(widths[index], " "))
        .join(" | ");
}

export function registerForgeListCommand(forge: Command): void {
    forge
        .command("list")
        .description("List available forge modules")
        .option("--app <app>", "Filter by app name or technical name")
        .action(async function (this: Command, options: { app?: string }) {
            const startedAt = Date.now();
            try {
                const globals = this.optsWithGlobals() as { engineUrl?: string; output?: string };
                const config = loadConfig({
                    engineUrl: globals.engineUrl,
                    outputPath: globals.output,
                });
                const client = new ForgeClient(config.engineUrl);
                const modules = await client.listModules({ app: options.app });
                if (modules.length === 0) {
                    console.log(warn("No modules found"));
                    return;
                }
                const rows = [
                    ["ID", "Name", "Technical Name", "State"],
                    ...modules.map((module) => [
                        String(module.id),
                        module.name,
                        module.technical_name,
                        module.state,
                    ]),
                ];
                const widths = [0, 0, 0, 0];
                for (const row of rows) {
                    row.forEach((value, index) => {
                        widths[index] = Math.max(widths[index], value.length);
                    });
                }
                console.log(tableRow(rows[0], widths));
                console.log(widths.map((width) => "-".repeat(width)).join("-+-"));
                for (const row of rows.slice(1)) {
                    console.log(tableRow(row, widths));
                }
                console.log(ok(`Listed ${modules.length} module${modules.length === 1 ? "" : "s"}`));
            } finally {
                console.log(info(`Done ${elapsed(Date.now() - startedAt)}`));
            }
        });
}
