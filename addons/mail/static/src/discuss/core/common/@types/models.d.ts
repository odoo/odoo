declare module "models" {
    export interface Store {
        readonly onlineMemberStatuses: String[],
        sortMembers(m1: ChannelMember, m2: ChannelMember)
    }

    export interface Thread {
        onlineMembers: ChannelMember[],
        offlineMembers: ChannelMember[],
        readonly hasMemberList: boolean,
        readonly notifyOnleave: boolean,
        private _computeOfflineMembers(): ChannelMember[],
    }
}
