import { Component, t, useProps, xml } from "@odoo/owl";
import { Notebook } from "@web/core/notebook/notebook";
import { Field } from "../fields/field";

/**
 * Displays a record with the template compiled from the arch, see
 * `compileFormArch`.
 */
export class FormRenderer extends Component {
    static template = xml`<t t-call="{{ this.props.archInfo.template }}"/>`;
    static components = { Field, Notebook };

    props = useProps({
        /** a record of the store */
        record: t.object(),
        /** @type {any} see `FormArchInfo` */
        archInfo: t.object(),
    });
}
