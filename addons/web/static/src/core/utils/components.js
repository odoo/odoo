/** @odoo-module **/

const { Component, xml } = owl;

export class NotUpdatable extends Component {
    shouldUpdate() {
        return false;
    }
}
NotUpdatable.template = xml`<t t-slot="default" />`;

export class ErrorHandler extends Component {
    catchError(error) {
        if (this.props.onError) {
            this.props.onError(error);
        }
    }
}
ErrorHandler.template = xml`<t t-slot="default" />`;
