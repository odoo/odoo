declare module "services" {
    import { ServicesRegistryShape } from "registries";

    import { errorService } from "@web/core/errors/error_service";
    import { fieldService } from "@web/core/field_service";
    import { fileUploadService } from "@web/core/file_upload/file_upload_service";
    import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
    import { httpService } from "@web/core/network/http_service";
    import { localizationService } from "@web/core/l10n/localization_service";
    import { multiCompanyRecoveryService } from "@web/core/multi_company_recovery_service";
    import { nameService } from "@web/core/name_service";
    import { ormService } from "@web/core/network/orm_service";
    import { resultSetCacheInvalidatorService } from "@web/core/network/result_set_cache_invalidator_service";
    import { slowRpcService } from "@web/core/network/slow_rpc_service";
    import { sortableService } from "@web/core/utils/dnd/sortable_service";
    import { templateCompileCacheService } from "@web/core/template_compile_cache";
    import { titleService } from "@web/core/browser/title_service";
    import { treeProcessorService } from "@web/core/tree/tree_processor_service";
    import { webVitalsService } from "@web/core/network/web_vitals/web_vitals_service";

    import { publicInteractionService } from "@web/public/interaction_service";

    import { connectionRecoveryService } from "@web/components/errors/error_handlers";
    import { datetimePickerService } from "@web/components/datetime/datetime_picker_service";
    import { frequentEmojiService } from "@web/components/emoji_picker/frequent_emoji_service";

    import { bottomSheetService } from "@web/ui/bottom_sheet/bottom_sheet_service";
    import { commandService } from "@web/ui/commands/command_service";
    import { dialogService } from "@web/ui/dialog/dialog_service";
    import { dismissAlertService } from "@web/ui/alert/dismiss_alert_service";
    import { effectService } from "@web/ui/effects/effect_service";
    import { formDialogStackService } from "@web/ui/form_dialog_stack_service";
    import { notificationService } from "@web/ui/notification/notification_service";
    import { overlayService } from "@web/ui/overlay/overlay_service";
    import { popoverService } from "@web/ui/popover/popover_service";
    import { pwaService } from "@web/ui/pwa/pwa_service";
    import { scssErrorNotificationService } from "@web/ui/scss_error_display";
    import { tooltipService } from "@web/ui/tooltip/tooltip_service";
    import { uiService } from "@web/ui/ui_service";

    import { demoDataService } from "@web/views/settings/widgets/demo_data_service";
    import { fillTemporalService } from "@web/views/fill_temporal_service";
    import { userInviteService } from "@web/views/settings/widgets/user_invite_service";
    import { viewService } from "@web/views/view_service";

    import { actionService } from "@web/webclient/actions/action_service";
    import { colorSchemeService } from "@web/webclient/color_scheme/color_scheme_service";
    import { currencyService } from "@web/webclient/currency_service";
    import { densityService } from "@web/webclient/density/density_service";
    import { enterpriseSubscriptionService } from "@web/webclient/home_menu/enterprise_subscription_service";
    import { homeMenuService } from "@web/webclient/home_menu/home_menu_service";
    import { lazySession } from "@web/webclient/session_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { profilingService } from "@web/webclient/debug/profiling/profiling_service";
    import { reloadCompanyService } from "@web/webclient/reload_company_service";
    import { serviceWorkerService } from "@web/webclient/service_worker_service";
    import { shareTargetService } from "@web/webclient/share_target/share_target_service";

    type ExtractServiceFactory<T extends ServicesRegistryShape> = Awaited<
        ReturnType<T["start"]>
    >;
    export type ServiceFactories = {
        [P in keyof Services]: ExtractServiceFactory<Services[P]>;
    };

    export interface Services {
        action: typeof actionService;
        bottom_sheet: typeof bottomSheetService;
        color_scheme: typeof colorSchemeService;
        command: typeof commandService;
        connection_recovery: typeof connectionRecoveryService;
        currency: typeof currencyService;
        datetime_picker: typeof datetimePickerService;
        demo_data: typeof demoDataService;
        density: typeof densityService;
        dialog: typeof dialogService;
        dismiss_alert: typeof dismissAlertService;
        effect: typeof effectService;
        enterprise_subscription: typeof enterpriseSubscriptionService;
        error: typeof errorService;
        field: typeof fieldService;
        file_upload: typeof fileUploadService;
        fillTemporalService: typeof fillTemporalService;
        form_dialog_stack: typeof formDialogStackService;
        home_menu: typeof homeMenuService;
        hotkey: typeof hotkeyService;
        http: typeof httpService;
        lazy_session: typeof lazySession;
        localization: typeof localizationService;
        menu: typeof menuService;
        multi_company_recovery: typeof multiCompanyRecoveryService;
        name: typeof nameService;
        notification: typeof notificationService;
        orm: typeof ormService;
        overlay: typeof overlayService;
        popover: typeof popoverService;
        profiling: typeof profilingService;
        "public.interactions": typeof publicInteractionService;
        pwa: typeof pwaService;
        reloadCompany: typeof reloadCompanyService;
        result_set_cache_invalidator: typeof resultSetCacheInvalidatorService;
        scss_error_display: typeof scssErrorNotificationService;
        service_worker: typeof serviceWorkerService;
        shareTarget: typeof shareTargetService;
        slow_rpc: typeof slowRpcService;
        sortable: typeof sortableService;
        template_compile_cache: typeof templateCompileCacheService;
        title: typeof titleService;
        tooltip: typeof tooltipService;
        tree_processor: typeof treeProcessorService;
        ui: typeof uiService;
        user_invite: typeof userInviteService;
        view: typeof viewService;
        "web.frequent.emoji": typeof frequentEmojiService;
        web_vitals: typeof webVitalsService;
    }
}
