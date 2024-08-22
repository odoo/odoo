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

    static template = xml`
    <div class="w-100 d-flex justify-content-between align-items-center bg-light rounded ps-2 pe-3 py-1 mb-2 gap-2">
        <div t-att-class="this.props.style === 'primary' ? 'odoo-bg-primary' : 'odoo-bg-secondary'" class="rounded" style="width: 7px !important; height: 50px" />
        <div class="flex-grow-1 overflow-hidden">
            <h6 class="m-0">
                <i t-if="this.props.icon" class="me-2 fa" t-att-class="this.props.icon" aria-hidden="true"></i>
                <t t-esc="this.props.name" />
            </h6>
            <p class="m-0 text-secondary one-line" t-esc="this.props.value" />
        </div>
        <div t-if="this.props.btnName">
            <button class="btn btn-primary btn-sm" t-esc="this.props.btnName" t-on-click="() => this.props.btnAction()" />
        </div>
        <t t-if="this.props.slots and this.props.slots['button']" t-slot="button" />
    </div>
  `;
}
