import { Component, useState } from "@odoo/owl";
import { Notebook } from "@web/core/notebook/notebook";
import { blockTab } from "./builder_tab/block_tab";
import { customizeTab } from "./builder_tab/customize_tab";

export class SnippetsMenu extends Component {
    static template = "mysterious_egg.SnippetsMenu";
    static components = { Notebook };

    setup() {
        this.pages = [blockTab, customizeTab];
        this.state = useState({ canUndo: true, canRedo: true });
    }
}
