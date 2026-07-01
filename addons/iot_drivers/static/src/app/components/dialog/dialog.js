/* global owl */

const { Component, xml, useListener, signal, props, types: t } = owl;

export class Dialog extends Component {
    props = props({
        name: t.string(),
        help: t.string().optional(),
        btnName: t.string().optional(),
        isLarge: t.boolean().optional(),
        onOpen: t.function().optional(() => () => {}),
        onClose: t.function().optional(() => () => {}),
    });

    dialogRef = signal(null, { type: t.ref() });

    setup() {
        useListener(this.dialogRef, "show.bs.modal", this.props.onOpen);
        useListener(this.dialogRef, "hide.bs.modal", this.props.onClose);
    }

    get identifier() {
        return this.props.name.toLowerCase().replace(/\s+/g, "-");
    }

    static template = xml`
    <t t-translation="off">
        <button type="button" class="btn btn-primary btn-sm" data-bs-toggle="modal" t-att-data-bs-target="'#'+this.identifier" t-out="this.props.btnName" />
        <div t-ref="this.dialogRef" t-att-id="this.identifier" class="modal modal-dialog-scrollable fade" t-att-class="{'modal-lg': this.props.isLarge}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header gap-1">
                        <t t-out="this.props.name"/>
                        <a t-if="this.props.help" t-att-href="this.props.help" class="fa fa-question-circle text-decoration-none text-dark" target="_blank"/>
                    </div>
                    <div class="modal-body position-relative dialog-body">
                        <t t-call-slot="body" />
                    </div>
                    <div class="modal-footer justify-content-around justify-content-md-start flex-wrap gap-1 w-100">
                        <div class="d-flex gap-2">
                            <t t-call-slot="footer" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </t>
    `;
}
