import { Chatter } from "@mail/chatter/web_portal/chatter";

import { ProjectFollowerList } from "./project_follower_list";

export class ProjectChatter extends Chatter {
    static components = {
        ...Chatter.components,
        FollowerList: ProjectFollowerList,
    };
}
