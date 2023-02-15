// We do not define owl as the jsconfig paths handles that. The goto definitions then show the js code in owl.js
// If we were using the d.ts system, we would have a goto defintion to the d.ts file and not the source code.

declare const luxon: typeof import("luxon");

declare module "@odoo/owl" {
    export * from "@odoo/owl/dist/types/owl"
}

// declare const Qunit: typeof import("qunit"); => Because we add methods to QUnit, we define our own..
// @ts-ignore
declare const QUnit: QUnit;

// @ts-ignore
declare const $: typeof import("jquery"); 
