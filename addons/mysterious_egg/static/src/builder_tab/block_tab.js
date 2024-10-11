import { Component } from "@odoo/owl";

export class BlockTab extends Component {
    static template = "mysterious_egg.BlockTab";
}

export const blockTab = {
    Component: BlockTab,
    name: "block",
    title: "Block",
};
