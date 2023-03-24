/** @odoo-module **/

import { ErrorHandler, WithEnv } from "../utils/components";

import { Component, xml } from "@odoo/owl";

export class DialogContainer extends Component {
    handleError(error, dialog) {
        dialog.props.close();
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
DialogContainer.components = { ErrorHandler, WithEnv };
//Legacy : The div wrapping the t-foreach, is placed to avoid owl to delete non-owl dialogs.
//This div can be removed after removing all legacy dialogs.
DialogContainer.template = xml`
    <div class="o_dialog_container" t-att-class="{'modal-open': Object.keys(props.dialogs).length > 0}">
        <div>
            <t t-foreach="Object.values(props.dialogs)" t-as="dialog" t-key="dialog.id">
                <ErrorHandler onError="(error) => this.handleError(error, dialog)">
                    <WithEnv env="{ dialogData: dialog.dialogData }">
                        <t t-component="dialog.class" t-props="dialog.props"/>
                    </WithEnv>
                </ErrorHandler>
            </t>
        </div>
    </div>
`;
