/* global owl */

const { Component, xml, useListener, signal, useProps, types: t } = owl;

export class Dialog extends Component {
<<<<<<< f5560c7657133607e9bb7f4a96d8dadd22b89823
    props = useProps({
||||||| 9f2c735a8f9a783e666ec0d94eb692ce782c450e
    props = props({
        slots: t.object(),
=======
    props = useProps({
        slots: t.object(),
>>>>>>> a4453c9b47973bc206d4cda390dfcc8be134e1ff
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
                        <a t-if="this.props.help" t-att-href="this.props.help" class="oi text-decoration-none text-dark" data-icon="help" target="_blank"/>
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
