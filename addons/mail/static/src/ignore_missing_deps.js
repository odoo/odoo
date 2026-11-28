// @odoo-module ignore

// The composer and the modules depending on it wait for the editor, which is
// lazy loaded (see `LazyComposer`): don't report them as missing dependencies.
window.__odooIgnoreMissingDependencies = true;
Promise.resolve().then(() => (window.__odooIgnoreMissingDependencies = false));
