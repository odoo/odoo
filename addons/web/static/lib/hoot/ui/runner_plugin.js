/** @odoo-module */

import { Plugin, t, useConfig, usePlugin } from "@odoo/owl";
import { Runner } from "../core/runner";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function getConfigPlugin() {
    return usePlugin(RunnerPlugin).instance.config;
}

export function getRunnerPlugin() {
    return usePlugin(RunnerPlugin).instance;
}

export class RunnerPlugin extends Plugin {
    instance = useConfig("runner", t.instanceOf(Runner));
}
