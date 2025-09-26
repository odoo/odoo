import { _t } from "@web/core/l10n/translation";
import { parseXML } from "@web/core/utils/xml";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useBus, useOwnedDialogs, useService } from "@web/core/utils/hooks";

import {
    Component,
    EventBus,
    onMounted,
    onWillStart,
    reactive,
    useExternalListener,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { RPCError } from "@web/core/network/rpc";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useSetupAction } from "@web/search/action_hook";
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

export class QuickCreateState {
    constructor(view) {
        this.view = view;
        this.isOpen = false;
        this.id = null;
        this.bus = new EventBus();
        return reactive(this);
    }

    async openQuickCreate(id) {
        // constraint: only one quick create open at a time, so notify that we will open
        // such that if there's one quick create already open, it can close itself first
        const canProceed = await this._willOpenQuickCreate(id);
        if (!canProceed) {
            return false;
        }
        this.isOpen = true;
        this.id = id;
        return true;
    }
    async closeQuickCreate() {
        this.isOpen = false;
        this.id = null;
    }

    async _willOpenQuickCreate(id) {
        const proms = [];
        this.bus.trigger("WILL-OPEN-QUICK-CREATE", { id, proms });
        const res = await Promise.all(proms);
        return !res.includes(false);
    }
}

export class KanbanQuickCreateController extends Component {
    static props = {
        Model: Function,
        Renderer: Function,
        Compiler: Function,
        quickCreateState: QuickCreateState,
        resModel: String,
        onValidate: Function,
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
            this.props.Model.services.map((servName) => [servName, useService(servName)])
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
        const modelParams = {
            config,
            useSendBeaconToSaveUrgently: true,
        };
        this.model = useState(new this.props.Model(this.env, modelParams, modelServices));

        onWillStart(async () => {
            await this.model.load();
            this.model.whenReady.resolve();
        });

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
            async (/** @type {MouseEvent} */ ev) => {
                if (this.uiActiveElement !== this.uiService.activeElement) {
                    // this component isn't in the current active element -> do nothing
                    return;
                }
                const target = this.mousedownTarget || ev.target;
                if (!this.rootRef.el.contains(target)) {
                    const isSameOverlay =
                        this.rootRef.el.closest(".o-overlay-item") ===
                        target.closest(".o-overlay-item");
                    if (isSameOverlay) {
                        if (!target.closest(".o_kanban_quick_add,.o-kanban-button-new")) {
                            await this.validate("close");
                        }
                    }
                }
                this.mousedownTarget = null;
            },
            { capture: true }
        );

        this._validateProm = null;

        // Validate when requested by the state
        useBus(this.props.quickCreateState.bus, "WILL-OPEN-QUICK-CREATE", (ev) => {
            const mode = ev.detail.id === this.props.quickCreateState.id ? "add" : "close";
            ev.detail.proms.push(this.validate(mode));
        });

        // Validate when leaving the view
        useSetupAction({
            beforeLeave: () => this.validate("close"),
            beforeUnload: (ev) => this.beforeUnload(ev),
            beforeVisibilityChange: () => this.beforeVisibilityChange(),
        });

        // Key Navigation
        useHotkey("enter", () => this.validate("add"), {
            area: () => this.rootRef.el.querySelector(".o_kanban_quick_create_form"),
            bypassEditableProtection: true,
        });
        useHotkey("escape", () => this.cancel(true));
    }

    get useNameCreate() {
        const fieldNames = Object.keys(this.model.root.activeFields);
        return fieldNames.length === 1 && fieldNames[0] === "display_name";
    }

    async beforeUnload(ev) {
        if (this.useNameCreate) {
            const name = this.model.root.data.display_name;
            if (name) {
                return this.nameCreate(name);
            }
        }
        const succeeded = await this.model.root.urgentSave();
        if (!succeeded) {
            ev.preventDefault();
            ev.returnValue = "Unsaved changes";
        }
    }

    beforeVisibilityChange() {
        if (document.visibilityState === "hidden") {
            return this.validate("close");
        }
    }

    validate(mode) {
        if (!this._validateProm) {
            this._validateProm = this._validate(mode);
            this._validateProm.then(() => (this._validateProm = null));
        }
        return this._validateProm;
    }

    /**
     * @param {"add"|"edit"|"close"} mode
     * @returns boolean
     */
    async _validate(mode) {
        if (mode === "close" && !(await this.model.root.isDirty())) {
            this.props.quickCreateState.closeQuickCreate();
            return true;
        }
        this.state.disabled = true;
        const resId = await this.save();
        if (resId) {
            this.props.onValidate(resId, mode);
            if (mode === "add") {
                await this.model.load({ resId: false });
            } else {
                this.props.quickCreateState.closeQuickCreate();
            }
            this.state.disabled = false;
            return true;
        } else {
            this.state.disabled = false;
            return false;
        }
    }

    async save() {
        let resId = this.model.root.resId;
        if (this.useNameCreate) {
            const isValid = await this.model.root.checkValidity(); // needed to put the class o_field_invalid in the field
            if (isValid) {
                try {
                    [resId] = await this.nameCreate(this.model.root.data.display_name);
                } catch (e) {
                    this.showFormDialogInError(e);
                }
                await this.model.root.discard();
            } else {
                this.model.notification.add(_t("Invalid Display Name"), { type: "danger" });
            }
        } else {
            await this.model.root.save({
                reload: false,
                onError: (e) => this.showFormDialogInError(e),
            });
            resId = this.model.root.resId;
        }
        return resId;
    }

    nameCreate(name) {
        const { resModel, context } = this.props;
        return this.model.orm.call(resModel, "name_create", [name], { context });
    }

    async cancel(force) {
        if (this.state.disabled) {
            return;
        }
        if (force || !(await this.model.root.isDirty())) {
            this.props.quickCreateState.closeQuickCreate();
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
        quickCreateState: QuickCreateState,
        onValidate: Function,
        resModel: String,
        context: Object,
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
        let quickCreateFields = { fields: DEFAULT_QUICK_CREATE_FIELDS };
        let quickCreateForm = DEFAULT_QUICK_CREATE_VIEW;
        let quickCreateRelatedModels = {};

        if (props.quickCreateState.view) {
            const { fields, relatedModels, views } = await this.viewService.loadViews({
                context: { ...props.context, form_view_ref: props.quickCreateState.view },
                resModel: props.resModel,
                views: [[false, "form"]],
            });
            quickCreateFields = { fields: fields };
            quickCreateForm = views.form;
            quickCreateRelatedModels = relatedModels;
        }
        const models = {
            ...quickCreateRelatedModels,
            [props.resModel]: quickCreateFields,
        };
        const archInfo = new formView.ArchParser().parse(
            parseXML(quickCreateForm.arch),
            models,
            props.resModel
        );
        this.quickCreateProps = {
            Model: formView.Model,
            Renderer: formView.Renderer,
            Compiler: formView.Compiler,
            resModel: props.resModel,
            onValidate: props.onValidate,
            fields: quickCreateFields.fields,
            context: props.context,
            archInfo,
            quickCreateState: props.quickCreateState,
        };
    }
}
