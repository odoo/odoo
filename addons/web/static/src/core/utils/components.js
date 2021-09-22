/** @odoo-module **/

const { Component, tags } = owl;

export class NotUpdatable extends Component {
    shouldUpdate() {
        return false;
    }
}
NotUpdatable.template = tags.xml`<t t-slot="default" />`;

export class ErrorHandler extends Component {
    catchError(error) {
        if (this.props.onError) {
            this.props.onError(error);
        }
    }
}
ErrorHandler.template = tags.xml`<t t-slot="default" />`;
