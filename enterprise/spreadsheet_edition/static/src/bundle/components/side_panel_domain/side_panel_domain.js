import { Component } from "@odoo/owl";
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { components } from "@odoo/o-spreadsheet";

const { Section } = components;

export class SidePanelDomain extends Component {
    static template = "spreadsheet_edition.SidePanelDomain";
    static components = {
        DomainSelector,
        Section,
    };
    static props = {
        resModel: String,
        domain: [Domain, String, Array],
        onUpdate: Function,
    };

    getStringifiedDomain() {
        return new Domain(this.props.domain).toString();
    }

    setup() {
        this.dialog = useService("dialog");
    }

    openDomainEdition() {
        this.dialog.add(DomainSelectorDialog, {
            resModel: this.props.resModel,
            domain: this.getStringifiedDomain(),
            isDebugMode: !!this.env.debug,
            onConfirm: (domain) => {
                this.props.onUpdate(new Domain(domain).toJson());
            },
        });
    }
}
