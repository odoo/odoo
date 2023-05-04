/** @odoo-module */
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

import {
    Component,
    onMounted,
    useExternalListener,
    useState,
    useRef,
    onWillStart,
    useSubEnv,
} from "@odoo/owl";
import { getDefaultConfig } from "../view";
import { RPCError } from "@web/core/network/rpc_service";
import { FormViewDialog } from "../view_dialogs/form_view_dialog";
import { formView } from "../form/form_view";
import { useModel } from "../model";

const DEFAULT_QUICK_CREATE_VIEW = {
    // note: the required modifier is written in the format returned by the server
    arch: /* xml */ `
        <form>
            <field name="display_name" placeholder="Title" modifiers='{"required": true}' />
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

        this.model = useModel(
            this.props.Model,
            {
                resModel: this.props.resModel,
                resId: false,
                resIds: [],
                fields: this.props.fields,
                activeFields: this.props.archInfo.activeFields,
                viewMode: "form",
                rootType: "record",
                mode: "edit",
                component: this,
            },
            {
                ignoreUseSampleModel: true,
            }
        );

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
            const isValid = await this.model.root.checkValidity(true); // needed to put the class o_field_invalid in the field
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
                this.model.notificationService.add(this.model.env._t("Display Name"), {
                    title: this.model.env._t("Invalid fields: "),
                    type: "danger",
                });
            }
        } else {
            try {
                await this.model.root.save({ closable: true, noReload: true, throwOnError: true });
            } catch (e) {
                this.showFormDialogInError(e);
            }
            resId = this.model.root.resId;
        }

        if (resId) {
            await this.props.onValidate(resId, mode);
        }
        this.state.disabled = false;
    }

    cancel(force) {
        if (this.state.disabled) {
            return;
        }
        if (force || !this.model.root.isDirty) {
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
            title: this.env._t("Create"),
            onRecordSaved: async (record) => {
                await this.props.onValidate(record.resId, "add");
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
        resModel: String,
        context: Object,
        onValidate: Function,
        onCancel: Function,
        group: Object,
    };

    setup() {
        this.state = useState({
            isLoaded: false,
        });
        this.viewService = useService("view");
        onWillStart(() => {
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
                resModel: props.resModel,
                views: [[false, "form"]],
            });
            quickCreateFields = fields;
            quickCreateForm = views.form;
            quickCreateRelatedModels = relatedModels;
        }
        const models = {
            ...quickCreateRelatedModels,
            [props.resModel]: quickCreateFields,
        };
        const archInfo = new formView.ArchParser().parse(
            quickCreateForm.arch,
            models,
            props.resModel
        );
        const context = props.context || {};
        context[`default_${props.group.groupByField.name}`] = props.group.getServerValue();
        this.quickCreateProps = {
            Model: formView.Model,
            Renderer: formView.Renderer,
            Compiler: formView.Compiler,
            resModel: props.resModel,
            onValidate: props.onValidate,
            onCancel: props.onCancel,
            fields: quickCreateFields,
            context,
            archInfo,
        };
    }
}
