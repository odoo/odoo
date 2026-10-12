import { Component, xml, useProps, t } from "@odoo/owl";
import { useDomState } from "../utils";

export class BuilderComponent extends Component {
    static template = xml`<t t-if="this.state.isVisible"><t t-call-slot="default"/></t>`;
    props = useProps({
        slots: t.object(),
    });

    setup() {
        this.state = useDomState(
            (editingElement) => ({
                isVisible: !!editingElement,
            }),
            { checkEditingElement: false }
        );
    }
}
