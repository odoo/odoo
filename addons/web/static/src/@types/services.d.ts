declare module "services" {
    import { ServicesRegistryShape } from "registries";

    // Core infrastructure services
    import { httpService } from "@web/core/network/http_service";

    // Public services
    import { publicInteractionService } from "@web/public/interaction_service";

    // Domain services
    import { commandService } from "@web/services/commands/command_service";
    import { datetimePickerService } from "@web/services/datetimepicker_service";
    import { errorService } from "@web/services/error_service";
    import { fieldService } from "@web/services/field_service";
    import { fileUploadService } from "@web/services/file_upload_service";
    import { frequentEmojiService } from "@web/services/frequent_emoji_service";
    import { localizationService } from "@web/services/localization_service";
    import { hotkeyService } from "@web/services/hotkeys/hotkey_service";
    import { nameService } from "@web/services/name_service";
    import { ormService } from "@web/services/orm_service";
    import { pwaService } from "@web/services/pwa/pwa_service";
    import { sortableService } from "@web/services/sortable_service";
    import { titleService } from "@web/services/title_service";
    import { treeProcessorService } from "@web/services/tree_processor_service";
    import { uiService } from "@web/services/ui/ui_service";

    // UI overlay services
    import { bottomSheetService } from "@web/ui/bottom_sheet/bottom_sheet_service";
    import { dialogService } from "@web/ui/dialog/dialog_service";
    import { effectService } from "@web/ui/effects/effect_service";
    import { notificationService } from "@web/ui/notification/notification_service";
    import { overlayService } from "@web/ui/overlay/overlay_service";
    import { popoverService } from "@web/ui/popover/popover_service";
    import { tooltipService } from "@web/ui/tooltip/tooltip_service";

    // View services
    import { viewService } from "@web/views/view_service";

    // Webclient services
    import { actionService } from "@web/webclient/actions/action_service";
    import { currencyService } from "@web/webclient/currency_service";
    import { profilingService } from "@web/webclient/debug/profiling/profiling_service";
    import { densityService } from "@web/webclient/density/density_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { lazySession } from "@web/webclient/session_service";
    import { demoDataService } from "@web/views/settings/widgets/demo_data_service";
    import { userInviteService } from "@web/views/settings/widgets/user_invite_service";
    import { shareTargetService } from "@web/webclient/share_target/share_target_service";

    type ExtractServiceFactory<T extends ServicesRegistryShape> = Awaited<ReturnType<T["start"]>>;
    export type ServiceFactories = {
        [P in keyof Services]: ExtractServiceFactory<Services[P]>;
    };

    export interface Services {
        "public.interactions": typeof publicInteractionService;
        "web.frequent.emoji": typeof frequentEmojiService;
        action: typeof actionService;
        bottom_sheet: typeof bottomSheetService;
        command: typeof commandService;
        currency: typeof currencyService;
        datetime_picker: typeof datetimePickerService;
        demo_data: typeof demoDataService;
        density: typeof densityService;
        dialog: typeof dialogService;
        effect: typeof effectService;
        error: typeof errorService;
        field: typeof fieldService;
        file_upload: typeof fileUploadService;
        hotkey: typeof hotkeyService;
        http: typeof httpService;
        lazy_session: typeof lazySession;
        localization: typeof localizationService;
        menu: typeof menuService;
        name: typeof nameService;
        notification: typeof notificationService;
        orm: typeof ormService;
        overlay: typeof overlayService;
        pwa: typeof pwaService;
        popover: typeof popoverService;
        profiling: typeof profilingService;
        shareTarget: typeof shareTargetService;
        sortable: typeof sortableService;
        title: typeof titleService;
        tooltip: typeof tooltipService;
        tree_processor: typeof treeProcessorService;
        ui: typeof uiService;
        user_invite: typeof userInviteService;
        view: typeof viewService;
    }
}
