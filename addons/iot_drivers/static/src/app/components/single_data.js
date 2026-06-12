/* global owl */

const { Component, xml, props, types: t } = owl;

const URL_REGEXP =
    /((([A-Za-z]{3,9}:(?:\/\/)?)(?:[-;:&=+$,\w]+@)?[A-Za-z0-9.-]+|(?:www.|[-;:&=+$,\w]+@)[A-Za-z0-9.-]+)((?:\/[+~%/.\w-_]*)?\??(?:[-+=&;%@.\w_]*)#?(?:[\w]*))?)/;

export class SingleData extends Component {
    props = props({
        name: t.string(),
        value: t.string(),
        icon: t.string().optional(),
        style: t.string().optional("primary"),
        slots: t.object(["button"]).optional(),
        btnName: t.string().optional(),
        btnAction: t.function().optional(),
    });

    get valueIsURL() {
        if (this.props.value.match(URL_REGEXP)) {
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
                <t t-out="this.props.name" />
            </h6>
            <p t-if="!this.valueIsURL" class="m-0 text-secondary one-line" t-out="this.props.value or 'Not Configured'" />
            <a t-if="this.valueIsURL" t-att-href="this.props.value" target="_blank" class="m-0 text-secondary one-line" t-out="this.props.value" />
        </div>
        <div t-if="this.props.btnName">
            <button class="btn btn-primary btn-sm" t-out="this.props.btnName" t-on-click="() => this.props.btnAction()" />
        </div>
        <t t-if="this.props.slots and this.props.slots['button']" t-call-slot="button" />
    </div>
  `;
}
