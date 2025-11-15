import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class addBookmark extends Component {
    static template = "main_menu.AddBookmark";
    static components = { DropdownItem };
    static props = {};

    addBookmark() {
        rpc("/main_menu/bookmark/add", {
            bookmark: {
                name: window.document.title,
                url: window.location.href,
            }
        });
    }
}

registry.category("cogMenu").add("add-bookmark", { Component: addBookmark }, { sequence: 1 });
