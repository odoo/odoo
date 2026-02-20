import { Plugin } from "@html_editor/plugin";

export class DisableBannerCommandsPlugin extends Plugin {
    static id = "disable_banner_commands";
    static dependencies = ["banner"];
    resources = {
        is_banner_command_available_predicates: () => false,
    };
}
