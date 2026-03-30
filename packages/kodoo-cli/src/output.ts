import chalk from "chalk";

import type { DiffResult, ValidationError } from "./client.js";

export function ok(message: string): string {
    return `${chalk.green("[OK]")} ${message}`;
}

export function err(message: string): string {
    return `${chalk.red("[ERR]")} ${message}`;
}

export function warn(message: string): string {
    return `${chalk.yellow("[WARN]")} ${message}`;
}

export function info(message: string): string {
    return `${chalk.gray("[·]")} ${message}`;
}

export function elapsed(milliseconds: number): string {
    const seconds = milliseconds / 1000;
    const formatted = seconds >= 10 ? seconds.toFixed(0) : seconds.toFixed(1);
    return chalk.gray(`(${formatted}s)`);
}

function validationCategory(rule: string): string {
    if (rule.startsWith("model.")) {
        return "Model";
    }
    if (rule.startsWith("field.")) {
        return "Field";
    }
    if (rule.startsWith("view.")) {
        return "View";
    }
    if (rule.startsWith("menu.")) {
        return "Menu";
    }
    if (rule.startsWith("action.")) {
        return "Action";
    }
    if (rule.startsWith("group.") || rule.startsWith("access.")) {
        return "Security";
    }
    if (rule.startsWith("xmlid.") || rule.startsWith("xml.")) {
        return "XML";
    }
    if (rule.startsWith("module.")) {
        return "Module";
    }
    return "Other";
}

export function printValidationErrors(errors: ValidationError[]): void {
    const grouped = new Map<string, ValidationError[]>();
    for (const item of errors) {
        const category = validationCategory(item.rule);
        const current = grouped.get(category) ?? [];
        current.push(item);
        grouped.set(category, current);
    }
    const order = ["Module", "Model", "Field", "View", "Menu", "Action", "Security", "XML", "Other"];
    for (const category of order) {
        const items = grouped.get(category);
        if (!items || items.length === 0) {
            continue;
        }
        console.log(chalk.bold(category));
        for (const item of items) {
            console.log(`  ${item.entity}: ${item.message} ${chalk.gray(`[${item.rule}]`)}`);
        }
    }
}

export function printDiff(diff: DiffResult): void {
    for (const filePath of diff.added) {
        console.log(chalk.green(`+ ${filePath}`));
    }
    for (const filePath of diff.removed) {
        console.log(chalk.red(`- ${filePath}`));
    }
    for (const filePath of diff.changed) {
        console.log(chalk.yellow(`~ ${filePath}`));
    }
    console.log(
        chalk.bold(
            `${diff.changed.length} changed, ${diff.added.length} added, ${diff.removed.length} removed`,
        ),
    );
}
