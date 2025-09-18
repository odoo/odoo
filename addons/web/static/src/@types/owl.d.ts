declare module "@odoo/owl" {
    export * from "@odoo/owl/dist/types/owl";
}

// OWL's Schema type is patched in node_modules/@odoo/owl/dist/types/owl.d.ts
// to accept Record<string, any> — this allows Odoo's complex prop declarations
// (spread operators, nested shapes, {value: ...}) to pass type checking.
// The patch is applied automatically via the postinstall script.
