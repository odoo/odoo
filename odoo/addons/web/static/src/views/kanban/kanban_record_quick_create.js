/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { parseXML } from "@web/core/utils/xml";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";

import {
    Component,
    onMounted,
    onWillStart,
    useExternalListener,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { RPCError } from "@web/core/network/rpc_service";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { formView } from "../form/form_view";
import { getDefaultConfig } from "../view";
import { FormViewDialog } from "../view_dialogs/form_view_dialog";

const DEFAULT_QUICK_CREATE_VIEW = {
    // note: the required modifier is written in the format returned by the server
    arch: /* xml */ `
        <form>
            <field name="display_name" placeholder="Title" required="True" />
        </form>`,
};
const DEFAULT_QUICK_CREATE_FIELDS = {
    display_name: { string: "Display name", type: "char" },
};

const ACTION_SELECTORS = [
    ".o_kanban_quick_add",
    ".o_kanban_load_more button",
    ".o-kanban-button-new",
];

class KanbanQuickCreateController extends Component {
    static props = {
        Model: Function,
        Renderer: Function,
        Compiler: Function,
        resModel: String,
        onValidate: Function,
        onCancel: Function,
        fields: { type: Object },
        context: { type: Object },
        archInfo: { type: Object },
    };
    static template = "web.KanbanQuickCreateController";
    setup() {
        super.setup();

        this.uiService = useService("ui");
        this.rootRef = useRef("root");
        this.state = useState({ disabled: false });
        this.addDialog = useOwnedDialogs();

        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.props.archInfo,
            this.props.fields
        );

        const modelServices = Object.fromEntries(
            this.props.Model.services.map((servName) => {
                return [servName, useService(servName)];
            })
        );
        modelServices.orm = useService("orm");
        const config = {
            resModel: this.props.resModel,
            resId: false,
            resIds: [],
            fields,
            activeFields,
            isMonoRecord: true,
            mode: "edit",
            context: this.props.context,
        };
        this.model = useState(new this.props.Model(this.env, { config }, modelServices));

        onWillStart(() => this.model.load());

        onMounted(() => {
            this.uiActiveElement = this.uiService.activeElement;
        });
        // Close on outside click
        useExternalListener(window, "mousedown", (/** @type {MouseEvent} */ ev) => {
            // This target is kept in order to impeach close on outside click behavior if the click
            // has been initiated from the quickcreate root element (mouse selection in an input...)
            this.mousedownTarget = ev.target;
        });
        useExternalListener(
            window,
            "click",
            (/** @type {MouseEvent} */ ev) => {
                if (this.uiActiveElement !== this.uiService.activeElement) {
                    // this component isn't in the current active element -> do nothing
                    return;
                }
                const target = this.mousedownTarget || ev.target;
                // accounts for clicking on datetime picker and legacy autocomplete
                const gotClickedInside =
                    target.closest(".o_datetime_picker") ||
                    target.closest(".ui-autocomplete") ||
                    this.rootRef.el.contains(target);
                if (!gotClickedInside) {
                    let force = false;
                    for (const selector of ACTION_SELECTORS) {
                        const closestEl = target.closest(selector);
                        if (closestEl) {
                            force = true;
                            break;
                        }
                    }
                    this.cancel(force);
                }
                this.mousedownTarget = null;
            },
            { capture: true }
        );

        // Key Navigation
        useHotkey("enter", () => this.validate("add"), { bypassEditableProtection: true });
        useHotkey("escape", () => this.cancel(true));
    }

    async validate(mode) {
        let resId = undefined;
        if (this.state.disabled) {
            return;
        }
        this.state.disabled = true;

        const keys = Object.keys(this.model.root.activeFields);
        if (keys.length === 1 && keys[0] === "display_name") {
            const isValid = await this.model.root.checkValidity(); // needed to put the class o_field_invalid in the field
            if (isValid) {
                try {
                    [resId] = await this.model.orm.call(
                        this.props.resModel,
                        "name_create",
                        [this.model.root.data.display_name],
                        {
                            context: this.props.context,
                        }
                    );
                } catch (e) {
                    this.showFormDialogInError(e);
                }
            } else {
                this.model.notification.add(_t("Display Name"), {
                    title: _t("Invalid fields: "),
                    type: "danger",
                });
            }
        } else {
            await this.model.root.save({
                reload: false,
                onError: (e) => this.showFormDialogInError(e),
            });
            resId = this.model.root.resId;
        }

        if (resId) {
            await this.props.onValidate(resId, mode);
            if (mode === "add") {
                await this.model.load({ resId: false });
            }
        }
        this.state.disabled = false;
    }

    async cancel(force) {
        if (this.state.disabled) {
            return;
        }
        if (force || !(await this.model.root.isDirty())) {
            this.props.onCancel();
        }
    }

    showFormDialogInError(e) {
        // TODO: filter RPC errors more specifically (eg, for access denied, there is no point in opening a dialog)
        if (!(e instanceof RPCError)) {
            throw e;
        }

        const context = this.props.context;
        const values = this.model.root.data;
        context.default_name = values.name || values.display_name;
        this.addDialog(FormViewDialog, {
            resModel: this.props.resModel,
            context,
            title: _t("Create"),
            onRecordSaved: async (record) => {
                await this.props.onValidate(record.resId, "add");
                await this.model.load();
            },
        });
    }

    get className() {
        return "o_kanban_quick_create o_field_highlight shadow";
    }
}

export class KanbanRecordQuickCreate extends Component {
    static components = { KanbanQuickCreateController };
    static template = "web.KanbanRecordQuickCreate";
    static props = {
        quickCreateView: { type: [String, { value: null }], optional: 1 },
        onValidate: Function,
        onCancel: Function,
        group: Object,
    };

    setup() {
        this.state = useState({
            isLoaded: false,
        });
        this.viewService = useService("view");
        onMounted(() => {
            this.getQuickCreateProps(this.props).then(() => {
                this.state.isLoaded = true;
            });
        });
        useSubEnv({
            config: getDefaultConfig(),
        });
    }

    async getQuickCreateProps(props) {
        let quickCreateFields = DEFAULT_QUICK_CREATE_FIELDS;
        let quickCreateForm = DEFAULT_QUICK_CREATE_VIEW;
        let quickCreateRelatedModels = {};

        if (props.quickCreateView) {
            const { fields, relatedModels, views } = await this.viewService.loadViews({
                context: { ...props.context, form_view_ref: props.quickCreateView },
                resModel: props.group.resModel,
                views: [[false, "form"]],
            });
            quickCreateFields = fields;
            quickCreateForm = views.form;
            quickCreateRelatedModels = relatedModels;
        }
        const models = {
            ...quickCreateRelatedModels,
            [props.group.resModel]: quickCreateFields,
        };
        const archInfo = new formView.ArchParser().parse(
            parseXML(quickCreateForm.arch),
            models,
            props.group.resModel
        );
        this.quickCreateProps = {
            Model: formView.Model,
            Renderer: formView.Renderer,
            Compiler: formView.Compiler,
            resModel: props.group.resModel,
            onValidate: props.onValidate,
            onCancel: props.onCancel,
            fields: quickCreateFields,
            context: props.group.context,
            archInfo,
        };
    }
}
