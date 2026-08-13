// @odoo-module ignore
// ! WARNING: this module must be loaded after `module_loader` but cannot have dependencies !

(function (odoo) {
    "use strict";

    if (odoo.define.name.endsWith("(hoot)")) {
        return;
    }

    const name = `${odoo.define.name} (hoot)`;
    odoo.define = {
        [name](name, dependencies, factory) {
            return odoo.loader.define(name, dependencies, factory, !name.endsWith(".hoot"));
        },
    }[name];
})(globalThis.odoo);
