import { Component } from "@odoo/owl";

export class MassMailingBuilderSelectLabel extends Component {
    static template = "mass_mailing.BuilderSelectLabel";
    static props = {
        label: { type: String },
        description: { type: String },
    };
}
