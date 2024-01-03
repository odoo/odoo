// We do not define owl as the jsconfig paths handles that. The goto definitions then show the js code in owl.js
// If we were using the d.ts system, we would have a goto defintion to the d.ts file and not the source code.
declare module "@odoo/owl" {
    export * from "@odoo/owl/dist/types/owl";
}

declare module "@odoo/hoot" {
    export * from "@web/../lib/hoot/hoot";
}

declare module "@odoo/hoot-dom" {
    export * from "@web/../lib/hoot-dom/hoot-dom";
}

declare module "@odoo/hoot-mock" {
    export * from "@web/../lib/hoot/hoot-mock";
}

type Factory<T = string> = (require: (dependency: T) => any) => any;

class ModuleLoader {
    define: <T = string>(name: string, deps: T[], factory: Factory<T>, lazy?: boolean) => void;
    factories: Map<string, { fn: Factory; deps: string[] }>;
    failed: Set<string>;
    jobs: Set<string>;
    modules: Map<string, any>;
}

declare const luxon: typeof import("luxon");

declare const odoo: {
    csrf_token: string;
    debug: string;
    define: (typeof ModuleLoader)["prototype"]["define"];
    loader: ModuleLoader;
};

// declare const Qunit: typeof import("qunit"); => Because we add methods to QUnit, we define our own..
// @ts-ignore
declare const QUnit: QUnit;

// @ts-ignore
declare const $: typeof import("jquery");
