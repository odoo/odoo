import { render } from "@web/owl2/utils";
import { Component, onWillStart, onWillUpdateProps, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { isId } from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
import { RecordAutocomplete } from "./record_autocomplete";

export const recordSelectorProps = {
    // loose: subclasses (e.g. DomainSelectorSingleAutocomplete) also pass
    // expressions, and the base schema is still validated for them
    resId: t.any(),
    virtualRecord: t.object().optional(),
    resModel: t.string(),
    update: t.function(),
    domain: t.array().optional(),
    context: t.object().optional(),
    fieldString: t.string().optional(),
    placeholder: t.string().optional(),
    buildQuickCreate: t.function().optional(),
};

export class RecordSelector extends Component {
    props = useProps(recordSelectorProps);
    static components = { RecordAutocomplete };
    static template = "web.RecordSelector";

    setup() {
        this.nameService = useService("name");
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    get isAvatarModel() {
        // bof
        return ["res.partner", "res.users", "hr.employee", "hr.employee.public"].includes(
            this.props.resModel
        );
    }

    get hasAvatarImg() {
        return this.isAvatarModel && isId(this.props.resId);
    }

    async computeDerivedParams(props = this.props) {
        const displayNames = await this.getDisplayNames(props);
        this.displayName = this.getDisplayName(props, displayNames);
    }

    async getDisplayNames(props) {
        const ids = this.getIds(props);
        const displayNames = await this.nameService.loadDisplayNames(props.resModel, ids);
        if (props.virtualRecord?.display_name) {
            displayNames[false] = props.virtualRecord.display_name;
        }
        return displayNames;
    }

    getDisplayName(props = this.props, displayNames) {
        const { resId } = props;
        if (resId === false && !props.virtualRecord?.display_name) {
            return "";
        }
        return typeof displayNames[resId || false] === "string"
            ? displayNames[resId]
            : _t("Inaccessible/missing record ID: %s", resId);
    }

    getIds(props = this.props) {
        if (props.resId) {
            return [props.resId];
        }
        return [];
    }

    update(resIds) {
        this.props.update(resIds[0] || false);
        render(this, true);
    }
}
