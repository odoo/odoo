/** @odoo-module **/

import { ErrorHandler, NotUpdatable } from "../utils/components";

const { Component, xml } = owl;

export class DialogContainer extends Component {
    setup() {
        this.props.bus.addEventListener("UPDATE", this.render.bind(this));
    }

    close(id) {
        if (this.props.dialogs[id]) {
            this.props.dialogs[id].props.close();
        }
    }

    handleError(error, dialogId) {
        this.close(dialogId);
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
DialogContainer.components = { ErrorHandler, NotUpdatable };
//Legacy : The div wrapping the t-foreach, is placed to avoid owl to delete non-owl dialogs.
//This div can be removed after removing all legacy dialogs.
DialogContainer.template = xml`
    <div class="o_dialog_container" t-att-class="{'modal-open': Object.keys(props.dialogs).length > 0}">
        <div>
            <t t-foreach="Object.values(props.dialogs)" t-as="dialog" t-key="dialog.id">
                <NotUpdatable>
                    <ErrorHandler onError="(error) => this.handleError(error, dialog.id)">
                        <t t-component="dialog.class" t-props="dialog.props" isActive="dialog_last"/>
                    </ErrorHandler>
                </NotUpdatable>
            </t>
        </div>
    </div>
`;
