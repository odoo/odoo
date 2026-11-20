import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { Composer } from "@mail/core/common/composer";

// Not imported by the chatter, so that it can be displayed without the editor.
Object.assign(Chatter.components, { Composer });
