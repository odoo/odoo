/** @odoo-module */

import { Plugin, config, plugin, types as t } from "@odoo/owl";
import { Runner } from "../core/runner";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function getConfigPlugin() {
    return plugin(RunnerPlugin).instance.config;
}

export function getRunnerPlugin() {
    return plugin(RunnerPlugin).instance;
}

export class RunnerPlugin extends Plugin {
    instance = config("runner", t.instanceOf(Runner));
}
