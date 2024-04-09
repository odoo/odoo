declare module "services" {
    import { ServicesRegistryShape } from "registries";

    import { titleService } from "@web/core/browser/title_service";
    import { commandService } from "@web/core/commands/command_service";
    import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
    import { dialogService } from "@web/core/dialog/dialog_service";
    import { effectService } from "@web/core/effects/effect_service";
    import { fieldService } from "@web/core/field_service";
    import { fileUploadService } from "@web/core/file_upload/file_upload_service";
    import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
    import { localizationService } from "@web/core/l10n/localization_service";
    import { nameService } from "@web/core/name_service";
    import { httpService } from "@web/core/network/http_service";
    import { notificationService } from "@web/core/notifications/notification_service";
    import { ormService } from "@web/core/orm_service";
    import { overlayService } from "@web/core/overlay/overlay_service";
    import { popoverService } from "@web/core/popover/popover_service";
    import { uiService } from "@web/core/ui/ui_service";
    import { userService } from "@web/core/user_service";
    import { sortableService } from "@web/core/utils/sortable_service";
    import { publicComponentService } from "@web/public/public_component_service";
    import { viewService } from "@web/views/view_service";
    import { actionService } from "@web/webclient/actions/action_service";
    import { companyService } from "@web/webclient/company_service";
    import { profilingService } from "@web/webclient/debug/profiling/profiling_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { demoDataService } from "@web/webclient/settings_form_view/widgets/demo_data_service";
    import { userInviteService } from "@web/webclient/settings_form_view/widgets/user_invite_service";

    type ExtractServiceFactory<T extends ServicesRegistryShape> = Awaited<ReturnType<T["start"]>>;
    export type ServiceFactories = {
        [P in keyof Services]: ExtractServiceFactory<Services[P]>;
    };

    export interface Services {
        action: typeof actionService;
        command: typeof commandService;
        company: typeof companyService;
        datetime_picker: typeof datetimePickerService;
        demo_data: typeof demoDataService;
        dialog: typeof dialogService;
        effect: typeof effectService;
        field: typeof fieldService;
        file_upload: typeof fileUploadService;
        hotkey: typeof hotkeyService;
        http: typeof httpService;
        localization: typeof localizationService;
        menu: typeof menuService;
        name: typeof nameService;
        notification: typeof notificationService;
        orm: typeof ormService;
        overlay: typeof overlayService;
        popover: typeof popoverService;
        profiling: typeof profilingService;
        public_components: typeof publicComponentService;
        sortable: typeof sortableService;
        title: typeof titleService;
        ui: typeof uiService;
        user: typeof userService;
        user_invite: typeof userInviteService;
        view: typeof viewService;
    }
}
