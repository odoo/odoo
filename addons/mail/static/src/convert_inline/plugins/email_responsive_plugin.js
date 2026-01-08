import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ResponsivePlugin extends Plugin {
    static id = "ResponsivePlugin";

    // handle main container (layout) to table to center elements
    // also contains the style element with media queries

    // convert all containers with rows to tables
    // convert rows to tr
    // normalize col usage in rows
    // convert cols to td
    // if all children of a td are tables, create one
    // table to wrap them all, each table in a td in a tr (why?)
}

registry.category("mail-html-conversion-plugins").add(ResponsivePlugin.id, ResponsivePlugin);
