/** @odoo-module */

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class TwitterUsersAutocomplete extends AutoComplete {
    static timeout = 500;

    get autoCompleteRootClass() {
        return `${super.autoCompleteRootClass} o_social_twitter_users_autocomplete`;
    }
}

export class TwitterUsersAutocompleteField extends CharField {
    static template = "social_twitter.TwitterUsersAutocompleteField";
    static components = {
        ...CharField.components,
        AutoComplete: TwitterUsersAutocomplete
    }

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.value = "";
    }

    async selectTwitterUser(selectedSubjection) {
        const twitterUser = Object.getPrototypeOf(selectedSubjection);
        this.value = twitterUser.name;
        const twitterAccountId = await this.orm.call(
            'social.twitter.account',
            'create',
            [{
                name: twitterUser.name,
                twitter_id: twitterUser.id
            }]
        );

        await this.props.record.update({
            twitter_followed_account_id: [twitterAccountId, twitterUser.name]
        });
    }

    get sources() {
        return [{
            optionTemplate: "social_twitter.users_autocomplete_element",
            options: async (request) => {
                if(request.length < 2) {
                    return [];
                }
                const accountId = this.props.record.data.account_id[0];
                const userInfo = await this.orm.call(
                    'social.account',
                    'twitter_get_user_by_username',
                    [[accountId], request]
                );
                return userInfo ? [userInfo] : [];
            }
        }];
    }
}

export const twitterUsersAutocompleteField = {
    ...charField,
    component: TwitterUsersAutocompleteField,
};

registry.category("fields").add("twitter_users_autocomplete", twitterUsersAutocompleteField);
