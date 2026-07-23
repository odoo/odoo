import { Record } from "@web/model/record";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useViewButtons } from "@web/views/view_button/view_button_hook";

import { CardRenderer } from "./card_renderer";
import { CARD_ATTRIBUTE, CardArchParser } from "./card_arch_parser";

import { Component, signal, t, useProps, xml } from "@odoo/owl";

export const cardProps = {
    card: t.any(),
    resModel: t.any(),
    resId: t.any().optional(),
    fields: t.any(),
    className: t.any().optional(),
    Compiler: t.any().optional(),
    context: t.any().optional(),
    hooks: t.any().optional(),
    readonly: t.any().optional(),
    archiveRecord: t.any().optional(),
    deleteRecord: t.any().optional(),
    openRecord: t.any().optional(),
};

export class Card extends Component {
    static template = xml`
        <div class="o_card" t-att-class="this.props.className" t-ref="this.rootRef">
            <Record t-props="this.recordProps" t-slot-scope="data" t-key="this.key()">
                <CardRenderer record="data.record" t-props="this.rendererProps"/>
            </Record>
        </div>`;
    static components = {
        Record,
        CardRenderer,
    };
    props = useProps(cardProps);
    static CARD_ATTRIBUTE = CARD_ATTRIBUTE;

    rootRef = signal.ref();

    setup() {
        const resModel = this.props.resModel;
        const relatedModels = { [resModel]: { fields: this.props.fields } };
        const archInfo = new CardArchParser().parse(this.props.card, relatedModels, resModel);
        const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, this.props.fields);
        this.archInfo = archInfo;
        this.activeFields = activeFields;
        this.fields = fields;

        this.key = signal(1);
        useViewButtons(this.rootRef, {
            reload: () => {
                this.key.set(this.key + 1);
            },
        });
    }

    get recordProps() {
        return {
            activeFields: this.activeFields,
            fields: this.fields,
            resId: this.props.resId,
            resModel: this.props.resModel,
            context: this.props.context,
            hooks: this.props.hooks,
        };
    }

    get rendererProps() {
        return {
            archInfo: this.archInfo,
            Compiler: this.props.Compiler,
            archiveRecord: this.props.archiveRecord,
            deleteRecord: this.props.deleteRecord,
            openRecord: this.props.openRecord,
            readonly: this.props.readonly,
        };
    }
}
