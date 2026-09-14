// @ts-check
/** @odoo-module native */

import {
    Component,
    onMounted,
    onWillStart,
    status,
    useExternalListener,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { extractFieldsFromArchInfo } from "@web/model/relational_model";
import { formView } from "@web/views/form/form_view";
import { getDefaultConfig } from "@web/views/view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

const DEFAULT_QUICK_CREATE_VIEW = {
    arch: `
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

const log = makeLogger("web.view.kanban.quick_create");

export class KanbanQuickCreateController extends Component {
    /** @type {ReturnType<typeof useOwnedDialogs>} */
    addDialog;
    /** @type {import("services").ServiceFactories["notification"]} */
    notificationService;
    /** @type {import("@odoo/owl").Ref} */
    rootRef;
    /** @type {{ disabled: boolean }} */
    state;
    /** @type {import("services").ServiceFactories["ui"]} */
    uiService;
    /** @type {import("services").ServiceFactories["view"]} */
    viewService;

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
        this.notificationService = useService("notification");
        this.rootRef = useRef("root");
        this.state = useState({ disabled: false });
        this.addDialog = useOwnedDialogs();

        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.props.archInfo,
            this.props.fields,
        );

        const modelServices = Object.fromEntries(
            this.props.Model.services.map((servName) => [
                servName,
                useService(servName),
            ]),
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
        this.model = useState(
            new this.props.Model(this.env, { config }, modelServices),
        );

        onWillStart(async () => {
            await this.model.load();
            this.model.whenReady.resolve();
        });

        onMounted(() => {
            this.uiActiveElement = this.uiService.activeElement;
        });
        useExternalListener(window, "mousedown", (/** @type {Event} */ ev) => {
            this.mousedownTarget = ev.target;
        });
        useExternalListener(
            window,
            "click",
            (/** @type {Event} */ ev) => {
                if (this.uiActiveElement !== this.uiService.activeElement) {
                    return;
                }
                const target = /** @type {HTMLElement} */ (
                    this.mousedownTarget || ev.target
                );
                const gotClickedInside =
                    target.closest(".o_datetime_picker") ||
                    target.closest(".ui-autocomplete") ||
                    this.rootRef.el.contains(target);
                if (!gotClickedInside) {
                    this.cancel(
                        ACTION_SELECTORS.some((selector) => target.closest(selector)),
                    );
                }
                this.mousedownTarget = null;
            },
            { capture: true },
        );

        useHotkey("enter", () => this.validate("add"), {
            bypassEditableProtection: true,
        });
        useHotkey("escape", () => this.cancel(true));
    }

    /** @param {"add" | "edit"} mode */
    async validate(mode) {
        log.logic("validate", () => ({ mode, disabled: this.state.disabled }));
        let resId = undefined;
        if (this.state.disabled) {
            return;
        }
        this.state.disabled = true;

        try {
            const keys = Object.keys(this.model.root.activeFields);
            if (keys.length === 1 && keys[0] === "display_name") {
                const isValid = await this.model.root.checkValidity();
                if (isValid) {
                    try {
                        [resId] = await this.model.orm.call(
                            this.props.resModel,
                            "name_create",
                            [this.model.root.data.display_name],
                            {
                                context: this.props.context,
                            },
                        );
                    } catch (e) {
                        this.showFormDialogInError(e);
                    }
                } else {
                    this.notificationService.add(_t("Invalid Display Name"), {
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
                this.props.onValidate(resId, mode);
                if (mode === "add") {
                    await this.model.load({ resId: false });
                }
            }
        } finally {
            if (!resId || mode === "add") {
                this.state.disabled = false;
            }
        }
    }

    /** @param {boolean} force */
    async cancel(force) {
        log.logic("cancel", () => ({ force, disabled: this.state.disabled }));
        if (this.state.disabled) {
            return;
        }
        if (force || !(await this.model.root.isDirty())) {
            this.props.onCancel();
        }
    }

    /** @param {Error} e */
    showFormDialogInError(e) {
        if (!(e instanceof RPCError)) {
            throw e;
        }

        const values = this.model.root.data;
        const context = {
            ...this.props.context,
            default_name: values.name || values.display_name,
        };
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

    /** @returns {string} */
    get className() {
        return "o_kanban_quick_create o_field_highlight shadow";
    }
}

export class KanbanRecordQuickCreate extends Component {
    static components = { KanbanQuickCreateController };
    static template = "web.KanbanRecordQuickCreate";
    static props = {
        quickCreateView: { type: [String, { value: null }], optional: true },
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
            this.getQuickCreateProps(this.props)
                .then(() => {
                    if (status(this) !== "destroyed") {
                        this.state.isLoaded = true;
                    }
                })
                .catch((error) => {
                    if (status(this) === "destroyed") {
                        return;
                    }
                    this.props.onCancel();
                    throw error;
                });
        });
        useSubEnv({
            config: getDefaultConfig(),
        });
    }

    /** @param {Object} props */
    async getQuickCreateProps(props) {
        /** @type {any} */
        let quickCreateFields = { fields: DEFAULT_QUICK_CREATE_FIELDS };
        /** @type {any} */
        let quickCreateForm = DEFAULT_QUICK_CREATE_VIEW;
        let quickCreateRelatedModels = {};

        if (props.quickCreateView) {
            const result = await this.viewService.loadViews(
                /** @type {any} */ ({
                    context: {
                        ...props.group.context,
                        form_view_ref: props.quickCreateView,
                    },
                    resModel: props.group.resModel,
                    views: [[false, "form"]],
                }),
            );
            const { fields, relatedModels, views } = /** @type {any} */ (result);
            quickCreateFields = { fields: fields };
            quickCreateForm = views.form;
            quickCreateRelatedModels = relatedModels;
        }
        const models = {
            ...quickCreateRelatedModels,
            [props.group.resModel]: quickCreateFields,
        };
        const archInfo = new formView.ArchParser().parse(
            quickCreateForm.ir ?? quickCreateForm.arch,
            models,
            props.group.resModel,
        );
        this.quickCreateProps = {
            Model: formView.Model,
            Renderer: formView.Renderer,
            Compiler: formView.Compiler,
            resModel: props.group.resModel,
            onValidate: props.onValidate,
            onCancel: props.onCancel,
            fields: quickCreateFields.fields,
            context: props.group.context,
            archInfo,
        };
    }
}
