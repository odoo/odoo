import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class CompanyTeamShapesWidthOption extends BaseOptionComponent {
    static selector = ".s_company_team_shapes";
    static template = "mass_mailing.CompanyTeamShapesWidth";
}

export class CompanyTeamOptionPlugin extends Plugin {
    static id = "mass_mailing.CompanyTeamOption";
    resources = {
        builder_options: [withSequence(1, CompanyTeamShapesWidthOption)],
    };
}

registry.category("mass_mailing-plugins").add(CompanyTeamOptionPlugin.id, CompanyTeamOptionPlugin);
