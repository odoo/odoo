import { CustomizeMailingPlugin } from "../builder/plugins/customize_mailing_plugin";
import { RecordSnapshotPlugin } from "../builder/plugins/record_snapshot_option_plugin";
import { SnippetVisibilityPlugin } from "../builder/plugins/snippet_visibility_option_plugin";
import { MassMailingSocialMediaOptionPlugin } from "../builder/plugins/social_media_option_plugin";
import { VersionControlPlugin } from "../builder/plugins/version_control_plugin";
import { ViewInBrowserOptionPlugin } from "../builder/plugins/view_in_browser_option_plugin";

declare module "plugins" {
    interface SharedMethods {
        "mass_mailing.CustomizeMailingPlugin": SharedOf<typeof CustomizeMailingPlugin>;
        "mass_mailing.SnippetVisibility": SharedOf<typeof SnippetVisibilityPlugin>;
        massMailingSocialMediaOptionPlugin: SharedOf<typeof MassMailingSocialMediaOptionPlugin>;
        recordSnapshot: SharedOf<typeof RecordSnapshotPlugin>;
        versionControl: SharedOf<typeof VersionControlPlugin>;
        viewInBrowserOptionPlugin: SharedOf<typeof ViewInBrowserOptionPlugin>;
    }
}
