/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from '@web/views/fields/many2one/many2one_field';
import { useCommand } from "@web/core/commands/command_hook";

const { Component } = owl;

export class Many2oneAvatarUser extends Many2OneField {

    setup() {
        super.setup();
        const provide = async (env, options) => {
            const records = await this._searchAssignTo(options.searchValue, 10);
            return records.map((record) => ({
                name: record[1],
                action: () => {
                    this.update([{ id: record[0], display_name: record[1] }]);
                }
            }));
        };
        useCommand(
            this.env._t('Assign to ...'),
            () => {
                return {
                    configByNamespace: {
                        default: {
                            emptyMessage: this.env._t("No users found"),
                        },
                    },
                    placeholder: this.env._t("Select a user..."),
                    providers: [{ provide }],
                };
            },
            {
                category: "smart_action",
                hotkey: "alt+i",
                global: true
            }
        );
        useCommand(
            this.env._t("Assign/unassign to me"),
            () => {
                if (this.env.services.user.userId === this.props.value[0]) {
                    this.update([{}]);
                } else {
                    this.update([{ id: this.env.services.user.userId, display_name: this.env.services.user.name }]);
                }
            },
            {
                category: "smart_action",
                hotkey: "alt+shift+i",
                global: true,
            }
        );
    }

    async _searchAssignTo(searchValue, limit) {
        const value = searchValue.trim();

        const nameSearch = await this.orm.call(
            this.props.relation,
            'name_search',
            {},
            {
                name: value,
                args: this.getDomain(),
                operator: "ilike",
                limit: limit + 1,
                context: this.context,
            }
        );
        return nameSearch;
    }

    get url() {
        return `/web/image/${this.props.relation}/${this.props.value[0]}/avatar_128`;
    }

    get displayName() {
        return this.props.value[1];
    }

    async openChat(ev) {
        ev.stopPropagation();
        const messaging = await Component.env.services.messaging.get();
        messaging.openChat({ userId: this.props.value[0] });
    }
}

Many2oneAvatarUser.supportedTypes = ['many2one'];
Many2oneAvatarUser.components = { Many2OneField };
Many2oneAvatarUser.props = { ...Many2OneField.props };
Many2oneAvatarUser.template = 'mail.Many2oneAvatarUser';
Many2oneAvatarUser.extractProps = Many2OneField.extractProps;

registry.category('fields').add('many2one_avatar_user', Many2oneAvatarUser);
