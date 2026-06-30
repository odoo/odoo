/* global owl */

const { Component, xml } = owl;

export class SingleData extends Component {
    static props = {
        name: String,
        value: String,
        icon: { type: String, optional: true },
        style: { type: String, optional: true },
        slots: { type: Object, optional: true },
        btnName: { type: String, optional: true },
        btnAction: { type: Function, optional: true },
    };
    static defaultProps = {
        style: "primary",
    };

    get valueIsURL() {
        const expression =
            /((([A-Za-z]{3,9}:(?:\/\/)?)(?:[-;:&=+$,\w]+@)?[A-Za-z0-9.-]+|(?:www.|[-;:&=+$,\w]+@)[A-Za-z0-9.-]+)((?:\/[+~%/.\w-_]*)?\??(?:[-+=&;%@.\w_]*)#?(?:[\w]*))?)/;

        const regex = new RegExp(expression);
        if (this.props.value?.match(regex)) {
            return true;
        } else {
            return false;
        }
    }

    static template = xml`
    <div class="w-100 d-flex justify-content-between align-items-center bg-light rounded ps-2 pe-3 py-1 mb-2 gap-2" t-translation="off">
        <div t-att-class="this.props.style === 'primary' ? 'odoo-bg-primary' : 'odoo-bg-secondary'" class="rounded odoo-pill" />
        <div class="flex-grow-1 overflow-hidden">
            <h6 class="m-0">
                <i t-if="this.props.icon" class="me-2 fa" t-att-class="this.props.icon" aria-hidden="true"></i>
                <t t-esc="this.props.name" />
            </h6>
            <p t-if="!this.valueIsURL" class="m-0 text-secondary one-line" t-esc="this.props.value or 'Not Configured'" />
            <a t-if="this.valueIsURL" t-att-href="this.props.value" target="_blank" class="m-0 text-secondary one-line" t-esc="this.props.value" />
        </div>
        <div t-if="this.props.btnName">
            <button class="btn btn-primary btn-sm" t-esc="this.props.btnName" t-on-click="() => this.props.btnAction()" />
        </div>
        <t t-if="this.props.slots and this.props.slots['button']" t-slot="button" />
    </div>
  `;
}
