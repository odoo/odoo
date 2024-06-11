declare module "services" {
    import { actionService } from "@web/webclient/actions/action_service";
    import { commandService } from "@web/core/commands/command_service";
    import { companyService } from "@web/webclient/company_service";
    import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
    import { dialogService } from "@web/core/dialog/dialog_service";
    import { effectService } from "@web/core/effects/effect_service";
    import { fieldService } from "@web/core/field_service";
    import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
    import { httpService } from "@web/core/network/http_service";
    import { menuService } from "@web/webclient/menus/menu_service";
    import { nameService } from "@web/core/name_service";
    import { notificationService } from "@web/core/notifications/notification_service";
    import { ormService } from "@web/core/orm_service";
    import { popoverService } from "@web/core/popover/popover_service";
    import { routerService } from "@web/core/browser/router_service";
    import { rpcService } from "@web/core/network/rpc_service";
    import { titleService } from "@web/core/browser/title_service";
    import { uiService } from "@web/core/ui/ui_service";
    import { userService } from "@web/core/user_service";
    import { viewService } from "@web/views/view_service";

    export interface Services {
        action: ReturnType<typeof actionService.start>;
        command: ReturnType<typeof commandService.start>;
        company: ReturnType<typeof companyService.start>;
        datetime_picker: ReturnType<typeof datetimePickerService.start>;
        dialog: ReturnType<typeof dialogService.start>;
        effect: ReturnType<typeof effectService.start>;
        field: ReturnType<typeof fieldService.start>;
        hotkey: ReturnType<typeof hotkeyService.start>;
        http: ReturnType<typeof httpService.start>;
        menu: Awaited<ReturnType<typeof menuService.start>>;
        name: ReturnType<typeof nameService.start>;
        notification: ReturnType<typeof notificationService.start>;
        orm: ReturnType<typeof ormService.start>;
        popover: ReturnType<typeof popoverService.start>;
        router: ReturnType<typeof routerService.start>;
        rpc: ReturnType<typeof rpcService.start>;
        title: ReturnType<typeof titleService.start>;
        ui: ReturnType<typeof uiService.start>;
        user: ReturnType<typeof userService.start>;
        view: ReturnType<typeof viewService.start>;
    }
}
