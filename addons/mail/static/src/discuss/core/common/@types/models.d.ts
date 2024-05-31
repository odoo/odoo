declare module "models" {
    export interface Store {
        sortOnlineMembers(m1: ChannelMember, m2: ChannelMember)
    }

    export interface Thread {
        onlineMembers: ChannelMember[],
        offlineMembers: ChannelMember[],
        readonly hasMemberList: boolean,
        private _computeOfflineMembers(): ChannelMember[],
    }
}
