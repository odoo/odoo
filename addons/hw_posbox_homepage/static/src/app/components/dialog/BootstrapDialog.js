/* global owl */

const { Component, xml, useEffect, useRef } = owl;

export class BootstrapDialog extends Component {
    static props = {
        identifier: String,
        slots: Object,
        btnName: { type: String, optional: true },
        onOpen: { type: Function, optional: true },
        onClose: { type: Function, optional: true },
    };

    setup() {
        this.dialog = useRef("dialog");

        useEffect(
            () => {
                if (!this.dialog || !this.dialog.el) {
                    return;
                }

                if (this.props.onOpen) {
                    this.dialog.el.addEventListener("show.bs.modal", this.props.onOpen);
                }

                if (this.props.onClose) {
                    this.dialog.el.addEventListener("hide.bs.modal", this.props.onClose);
                }

                return () => {
                    this.dialog.el.removeEventListener("show.bs.modal", this.props.onOpen);
                    this.dialog.el.removeEventListener("hide.bs.modal", this.props.onClose);
                };
            },
            () => [this.dialog]
        );
    }

    static template = xml`
        <button type="button" class="btn btn-primary btn-sm" data-bs-toggle="modal" t-att-data-bs-target="'#'+this.props.identifier" t-esc="this.props.btnName" />
        <div t-ref="dialog" t-att-id="this.props.identifier" class="modal modal-dialog-scrollable fade" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <t t-slot="header" />
                    </div>
                    <div class="modal-body position-relative" style="max-height: 70vh; min-height: 40vh;">
                        <t t-slot="body" />
                    </div>
                    <div class="modal-footer">
                        <t t-slot="footer" />
                    </div>
                </div>
            </div>
        </div>
    `;
}
