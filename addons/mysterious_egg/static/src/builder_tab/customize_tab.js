import { Component } from "@odoo/owl";

export class CustomizeTab extends Component {
    static template = "mysterious_egg.CustomizeTab";
}

export const customizeTab = {
    Component: CustomizeTab,
    name: "custom",
    title: "Customize",
};
