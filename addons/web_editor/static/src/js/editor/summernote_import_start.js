/**
 * This file allows the import of all summernote files.
 *
 * @todo The version we currently have is summernote v0.6.0 (source code
 * version). It is supposed to be used pre-compiled in one file or with its
 * correct dev dependencies. We use neither of those methods; instead we have
 * to call this setup file to declare the global `define` method and pipe the
 * results into our `odoo.define` architecture, and then to call the
 * dismantling function to clean the global scope. To properly import the files
 * we need to match the order of declared imports with the order in which the
 * files are loaded by the client, since they don't provide their own
 * file/module names in their declaration. This is obviously to remove as soon
 * as we remove/update summernote for a decent alternative.
 * @see summernote_import_end.js (dismantling script)
 */
(function () {
    "use strict";
    odoo.define("jquery", () => $);

    const SUMMERNOTE_MODULES = [
        'summernote/core/async',
        'summernote/core/func',
        'summernote/core/agent',
        'summernote/core/list',
        'summernote/core/dom',
        'summernote/core/key',
        'summernote/core/range',
        'summernote/editing/Bullet',
        'summernote/editing/History',
        'summernote/editing/Style',
        'summernote/editing/Table',
        'summernote/editing/Typing',
        'summernote/module/Editor',
        'summernote/module/Button',
        'summernote/module/Clipboard',
        'summernote/module/Codeview',
        'summernote/module/DragAndDrop',
        'summernote/module/Fullscreen',
        'summernote/module/Handle',
        'summernote/module/HelpDialog',
        'summernote/module/ImageDialog',
        'summernote/module/LinkDialog',
        'summernote/module/Popover',
        'summernote/module/Statusbar',
        'summernote/module/Toolbar',
        'summernote/Renderer',
        'summernote/EventHandler',
        'summernote/defaults',
        'summernote/summernote',
    ];

    odoo.__define__ = window.define;

    window.define = function (deps, factory) {
        const moduleId = SUMMERNOTE_MODULES.shift();
        if (Array.isArray(deps)) {
            const odooKey = `__summernote_module_${moduleId}`;
            const args = [];
            const reqs = [`f=odoo["${odooKey}"]`];
            for (let i = 0; i < deps.length; i++) {
                args.push(`m${i}`);
                reqs.push(`m${i}=require("${deps[i]}")`);
            }
            odoo[odooKey] = factory;
            factory = new Function(
                "require",
                `let ${reqs.join(",")};delete odoo["${odooKey}"];return f(${args.join(",")});`
            );
        }
        odoo.define(moduleId, factory);
    };
})();
