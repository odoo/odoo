import { props } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain } from "@web/model/relational_model/utils";

/**
 * Use this hook to add "Assign to.." and "Assign/Unassign me" to the command palette.
 */

export function useAssignUserCommand() {
    const compProps = props();
    const { relation, type } = compProps.record.fields[compProps.name];
    if (relation !== "res.users") {
        return;
    }

    const getCurrentIds = () => {
        if (type === "many2one" && getValue()) {
            return [getValue().id];
        } else if (type === "many2many") {
            return getValue().currentIds;
        }
        return [];
    };

    function getValue() {
        return compProps.record.data[compProps.name];
    }

    const add = async (record) => {
        if (type === "many2one") {
            compProps.record.update({
                [compProps.name]: {
                    id: record[0],
                    display_name: record[1],
                },
            });
        } else if (type === "many2many") {
            getValue().linkTo(record[0], {
                display_name: record[1],
            });
        }
    };

    const remove = async (record) => {
        if (type === "many2one") {
            compProps.record.update({ [compProps.name]: false });
        } else if (type === "many2many") {
            getValue().unlinkFrom(record[0]);
        }
    };

    const provide = async (env, options) => {
        const value = options.searchValue.trim();
        let domain = getFieldDomain(compProps.record, compProps.name, compProps.domain);
        const context = compProps.context;
        if (type === "many2many") {
            const selectedUserIds = getCurrentIds();
            if (selectedUserIds.length) {
                domain = Domain.and([domain, [["id", "not in", selectedUserIds]]]).toList();
            }
        }
        pendingRpc?.abort(false);
        pendingRpc = orm.call(relation, "name_search", [], {
            name: value,
            domain: domain,
            operator: "ilike",
            limit: 80,
            context,
        });
        const searchResult = await pendingRpc;
        pendingRpc = null;
        return searchResult.map((record) => ({
            name: record[1],
            action: add.bind(null, record),
        }));
    };

    const orm = useService("orm");
    const options = {
        category: "smart_action",
        global: true,
        identifier: compProps.string,
    };
    if (compProps.record.id !== compProps.record.model.root.id) {
        // Only List View
        options.isAvailable = () => compProps.record.model.multiEdit && compProps.record.selected;
    } else {
        options.isAvailable = () => true;
    }

    /** @type {(Promise<any> | null)} */
    let pendingRpc = null;

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
    if (compProps.record.id === compProps.record.model.root.id) {
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
    } else if (type === "many2one") {
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
                isAvailable: () => options.isAvailable() && getCurrentIds().includes(user.userId),
                hotkey: "alt+shift+u",
            }
        );
    }
}
