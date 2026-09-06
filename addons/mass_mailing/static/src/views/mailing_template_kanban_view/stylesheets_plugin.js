import { Plugin, t, useConfig } from "@odoo/owl";

export class StyleSheetPlugin extends Plugin {
    promises = useConfig("styleSheetPromises", t.array(t.promise()));
}
