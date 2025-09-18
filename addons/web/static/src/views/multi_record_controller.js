// @ts-check

/** @module @web/views/multi_record_controller - Base controller class for multi-record views (list, kanban) */

/**
 * Base class for multi-record view controllers (list, kanban).
 *
 * Encapsulates the shared setup, getters, and methods that were previously
 * duplicated between ListController and KanbanController. Single-record views
 * (form) extend Component directly.
 *
 * Subclass contract:
 *   1. Call `super.setup()` first (initializes services, archInfo, rootRef, etc.)
 *   2. Initialize `this.model` (view-specific model + sample data)
 *   3. Call `this.initMultiRecordBehavior()` (wires viewButtons, selection tracking, etc.)
 *   4. Then add view-specific hooks (useSetupAction, usePager, scroll restoration…)
 */
import {
    Component,
    onMounted,
    onWillStart,
    useEffect,
    useRef,
    useSubEnv,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { user } from "@web/services/user";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useDeleteRecords, useExportRecords } from "@web/views/view_hook";
import {
    buildActionMenuItems,
    computeArchiveEnabled,
    computeModelOptions,
    useControllerServices,
} from "@web/views/view_utils";

export class MultiRecordController extends Component {
    /** @type {any} */
    model;

    // -------------------------------------------------------------------------
    // Setup
    // -------------------------------------------------------------------------

    setup() {
        // --- Services ---
        const { action, dialog, notification, orm, uiHooks } = useControllerServices();
        this.actionService = action;
        this.dialogService = dialog;
        this.notification = notification;
        this.orm = orm;
        this._uiHooks = uiHooks;

        // --- Arch / refs ---
        this.archInfo = this.props.archInfo;
        this.rootRef = useRef("root");

        // --- Shared state ---
        this.archiveEnabled = computeArchiveEnabled(this.props.fields);
        this.searchBarToggler = useSearchBarToggler();
        this.firstLoad = true;
        onMounted(() => {
            this.firstLoad = false;
        });
    }

    /**
     * Wire hooks that depend on `this.model` being initialized.
     * Must be called by the subclass after model creation.
     */
    initMultiRecordBehavior() {
        useSubEnv({ model: this.model });

        onWillStart(async () => {
            this.isExportEnable = await user.hasGroup("base.group_allow_export");
        });

        useViewButtons(this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
            reload: () => this.model.load(),
        });

        useEffect(
            () => {
                this.onSelectionChanged();
            },
            () => [this.model.root.selection?.length, this.model.root.isDomainSelected],
        );

        this.exportRecords = useExportRecords(this.env, this.props.context, () =>
            this.getExportableFields(),
        );
        this.deleteRecordsWithConfirmation = useDeleteRecords(this.model);
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get actionMenuItems() {
        return buildActionMenuItems(
            this.getStaticActionMenuItems(),
            this.props.info.actionMenus,
        );
    }

    get actionMenuProps() {
        return {
            getActiveIds: () => this.model.root.selection.map((r) => r.resId),
            context: this.model.root.context,
            domain: this.props.domain,
            items: this.actionMenuItems,
            isDomainSelected: this.model.root.isDomainSelected,
            resModel: this.model.root.resModel,
            onActionExecuted: (/** @type {any} */ { noReload } = {}) => {
                if (!noReload) {
                    return this.model.load();
                }
            },
        };
    }

    get display() {
        const { controlPanel } = this.props.display;
        if (!controlPanel) {
            return this.props.display;
        }
        return {
            ...this.props.display,
            controlPanel: {
                ...controlPanel,
                layoutActions: !this.hasSelectedRecords,
            },
        };
    }

    get hasSelectedRecords() {
        return this.model.root.selection?.length || this.isDomainSelected;
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    get modelOptions() {
        return computeModelOptions(this.env, this.props.display);
    }

    get archiveDialogProps() {
        return {};
    }

    get deleteConfirmationDialogProps() {
        return {};
    }

    // -------------------------------------------------------------------------
    // Action menu
    // -------------------------------------------------------------------------

    getStaticActionMenuItems() {
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "fa fa-upload",
                description: _t("Export"),
                callback: () => this.exportRecords(),
            },
            duplicate: {
                isAvailable: () => this.archInfo.activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.model.root.duplicateRecords(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 40,
                icon: "oi oi-archive",
                description: _t("Archive"),
                callback: () =>
                    this.model.root.toggleArchiveWithConfirmation(
                        true,
                        this.archiveDialogProps,
                    ),
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled,
                sequence: 45,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.toggleArchiveWithConfirmation(false),
            },
            delete: {
                isAvailable: () => this.archInfo.activeActions.delete,
                sequence: 50,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                class: "text-danger",
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }

    // -------------------------------------------------------------------------
    // Extension points
    // -------------------------------------------------------------------------

    /** Override to provide view-specific exportable fields. */
    getExportableFields() {
        return [];
    }

    /** Called when selection changes. Override to react to selection. */
    async onSelectionChanged() {
        if (this.props.onSelectionChanged) {
            const resIds = await this.model.root.getResIds(true);
            this.props.onSelectionChanged(resIds);
        }
    }

    /** Scroll to top after pager navigation. Override for view-specific selector. */
    onPageChangeScroll() {
        if (this.rootRef?.el) {
            if (this.env.isSmall) {
                this.rootRef.el.scrollTop = 0;
            } else {
                this.rootRef.el.querySelector(".o_content").scrollTop = 0;
            }
        }
    }

    /** Wraps deletion with confirmation dialog. Override for custom delete flows. */
    onDeleteSelectedRecords() {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps);
    }

    /** Intercept action button execution. Return false to prevent execution. */
    async beforeExecuteActionButton(clickParams) {}

    /** Post-processing after action button execution. */
    async afterExecuteActionButton(clickParams) {}
}
