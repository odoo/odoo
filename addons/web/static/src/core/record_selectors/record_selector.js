import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { isId } from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
import { RecordAutocomplete } from "./record_autocomplete";

export class RecordSelector extends Component {
    static props = {
        resId: [Number, { value: false }],
        virtualRecord: { type: Object, optional: true },
        resModel: String,
        update: Function,
        domain: { type: Array, optional: true },
        context: { type: Object, optional: true },
        fieldString: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        buildQuickCreate: { type: Function, optional: true },
    };
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
        this.render(true);
    }
}
