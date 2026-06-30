/* @odoo-module */

import { useComponent } from "@odoo/owl";

import { useCommand } from "@web/core/commands/command_hook";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Use this hook to add "Assign to.." and "Assign/Unassign me" to the command palette.
 */

export function useAssignUserCommand() {
    const component = useComponent();
    const orm = useService("orm");
    const user = useService("user");
    const type = component.props.record.fields[component.props.name].type;
    if (component.relation !== "res.users") {
        return;
    }

    const getCurrentIds = () => {
        if (type === "many2one" && component.props.record.data[component.props.name]) {
            return [component.props.record.data[component.props.name][0]];
        } else if (type === "many2many") {
            return component.props.record.data[component.props.name].currentIds;
        }
        return [];
    };

    const add = async (record) => {
        if (type === "many2one") {
            component.props.record.update({ [component.props.name]: record });
        } else if (type === "many2many") {
            component.props.record.data[component.props.name].linkTo(record[0], {
                display_name: record[1],
            });
        }
    };

    const remove = async (record) => {
        if (type === "many2one") {
            component.props.record.update({ [component.props.name]: false });
        } else if (type === "many2many") {
            component.props.record.data[component.props.name].unlinkFrom(record[0]);
        }
    };

    const provide = async (env, options) => {
        const value = options.searchValue.trim();
        let domain =
            typeof component.props.domain === "function"
                ? component.props.domain()
                : component.props.domain;
        const context = component.props.context;
        if (type === "many2many") {
            const selectedUserIds = getCurrentIds();
            if (selectedUserIds.length) {
                domain = Domain.and([domain, [["id", "not in", selectedUserIds]]]).toList();
            }
        }
        component._pendingRpc?.abort(false);
        component._pendingRpc = orm.call(component.relation, "name_search", [], {
            name: value,
            args: domain,
            operator: "ilike",
            limit: 80,
            context,
        });
        const searchResult = await component._pendingRpc;
        component._pendingRpc = null;
        return searchResult.map((record) => ({
            name: record[1],
            action: add.bind(null, record),
        }));
    };
    const options = {
        category: "smart_action",
        global: true,
        identifier: component.props.string,
    };
    if (component.props.record.id !== component.props.record.model.root.id) {
        // Only List View
        options.isAvailable = () =>
            component.props.record.model.multiEdit && component.props.record.selected;
    } else {
        options.isAvailable = () => true;
    }
    useCommand(
        _t("Assign to ..."),
        () => ({
            configByNameSpace: {
                default: {
                    emptyMessage: _t("No users found"),
                },
            },
            placeholder: _t("Select a user..."),
            providers: [
                {
                    provide,
                },
            ],
        }),
        {
            ...options,
            hotkey: "alt+i",
        }
    );

    useCommand(
        _t("Assign to me"),
        () => {
            add([user.userId, user.name]);
        },
        {
            ...options,
            isAvailable: () => options.isAvailable() && !getCurrentIds().includes(user.userId),
            hotkey: "alt+shift+i",
        }
    );
    if (component.props.record.id === component.props.record.model.root.id) {
        // Only Form View
        useCommand(
            _t("Unassign from me"),
            () => {
                remove([user.userId, user.name]);
            },
            {
                ...options,
                isAvailable: () => options.isAvailable() && getCurrentIds().includes(user.userId),
                hotkey: "alt+shift+i",
            }
        );
    } else {
        if (type === "many2one") {
            useCommand(
                _t("Unassign"),
                () => {
                    remove([user.userId, user.name]);
                },
                {
                    ...options,
                    isAvailable: () => options.isAvailable() && getCurrentIds().length > 0,
                    hotkey: "alt+shift+u",
                }
            );
        } else {
            useCommand(
                _t("Unassign from me"),
                () => {
                    remove([user.userId, user.name]);
                },
                {
                    ...options,
                    isAvailable: () =>
                        options.isAvailable() && getCurrentIds().includes(user.userId),
                    hotkey: "alt+shift+u",
                }
            );
        }
    }
}
