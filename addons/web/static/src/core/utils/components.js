/** @odoo-module **/

const { Component, onError, useComponent, xml } = owl;

export class NotUpdatable extends Component {
    setup() {
        const node = useComponent().__owl__;
        node.patch = () => {};
        node.updateAndRender = () => Promise.resolve();
    }
}
NotUpdatable.template = xml`<t t-slot="default" />`;

export class ErrorHandler extends Component {
    setup() {
        onError((error) => {
            this.props.onError(error);
        });
    }
}
ErrorHandler.template = xml`<t t-slot="default" />`;
ErrorEvent.props = ["onError"];
