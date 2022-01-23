/** @odoo-module **/

const { Component, QWeb } = owl;

export class Icon extends Component {
    get iconTemplateName() {
        return 'web.oi_' + this.props.name;
    }

    get tone() {
        return this.props.tone;
    }
}

Icon.template = "web.Icon";
Icon.props = {
    name: { type: String, optional: true },
    tone: { type: String, optional: true },
};

QWeb.registerComponent("Icon", Icon);
