/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Partner
        [Model/fields]
            active
            avatarUrl
            country
            displayName
            email
            hasCheckedUser
            id
            imStatus
            isImStatusAway
            isImStatusOffline
            isImStatusOnline
            isOnline
            memberThreads
            model
            name
            nameOrDisplayName
            rtcSessions
            user
            volumeSetting
        [Model/id]
            Partner/id
        [Model/actions]
            Partner/_fetchImStatus
            Partner/_loopFetchImStatus
            Partner/checkIsUser
            Partner/convertData
            Partner/fetchSuggestions
            Partner/getChat
            Partner/getSuggestionSortFunction
            Partner/imSearch
            Partner/openChat
            Partner/openProfile
            Partner/searchSuggestions
            Partner/startLoopFetchImStatus
`;
