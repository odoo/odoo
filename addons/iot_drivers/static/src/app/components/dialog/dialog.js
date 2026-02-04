import { useLayoutEffect } from "@web/owl2/utils";
/* global owl */

const { Component, xml, useLayoutEffect, useRef } = owl;

export class Dialog extends Component {
    static props = {
        slots: Object,
        name: String,
        help: { type: String, optional: true },
        btnName: { type: String, optional: true },
        isLarge: { type: Boolean, optional: true },
        onOpen: { type: Function, optional: true },
        onClose: { type: Function, optional: true },
    };

    setup() {
        this.dialog = useRef("dialog");

        useLayoutEffect(
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

    get identifier() {
        return this.props.name.toLowerCase().replace(/\s+/g, "-");
    }

    static template = xml`
    <t t-translation="off">
        <button type="button" class="btn btn-primary btn-sm" data-bs-toggle="modal" t-att-data-bs-target="'#'+identifier" t-esc="this.props.btnName" />
        <div t-ref="dialog" t-att-id="identifier" class="modal modal-dialog-scrollable fade" t-att-class="{'modal-lg': props.isLarge}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header gap-1">
                        <t t-out="props.name"/>
                        <a t-if="props.help" t-att-href="props.help" class="fa fa-question-circle text-decoration-none text-dark" target="_blank"/>
                    </div>
                    <div class="modal-body position-relative dialog-body">
                        <t t-slot="body" />
                    </div>
                    <div class="modal-footer justify-content-around justify-content-md-start flex-wrap gap-1 w-100">
                        <div class="d-flex gap-2">
                            <t t-slot="footer" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </t>
    `;
}
