import { useComponent } from "@web/owl2/utils";

import { useCommand } from "@web/core/commands/command_hook";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { props } from "@odoo/owl";

/**
 * Use this hook to add "Assign to.." and "Assign/Unassign me" to the command palette.
 */

export function useAssignUserCommand() {
    const component = useComponent();
    const cprops = props();
    const orm = useService("orm");
    const type = cprops.record.fields[cprops.name].type;
    if (component.relation !== "res.users") {
        return;
    }

    const getCurrentIds = () => {
        if (type === "many2one" && cprops.record.data[cprops.name]) {
            return [cprops.record.data[cprops.name].id];
        } else if (type === "many2many") {
            return cprops.record.data[cprops.name].currentIds;
        }
        return [];
    };

    const add = async (record) => {
        if (type === "many2one") {
            cprops.record.update({
                [cprops.name]: {
                    id: record[0],
                    display_name: record[1],
                },
            });
        } else if (type === "many2many") {
            cprops.record.data[cprops.name].linkTo(record[0], {
                display_name: record[1],
            });
        }
    };

    const remove = async (record) => {
        if (type === "many2one") {
            cprops.record.update({ [cprops.name]: false });
        } else if (type === "many2many") {
            cprops.record.data[cprops.name].unlinkFrom(record[0]);
        }
    };

    const provide = async (env, options) => {
        const value = options.searchValue.trim();
        let domain = getFieldDomain(cprops.record, cprops.name, cprops.domain);
        const context = cprops.context;
        if (type === "many2many") {
            const selectedUserIds = getCurrentIds();
            if (selectedUserIds.length) {
                domain = Domain.and([domain, [["id", "not in", selectedUserIds]]]).toList();
            }
        }
        component._pendingRpc?.abort(false);
        component._pendingRpc = orm.call(component.relation, "name_search", [], {
            name: value,
            domain: domain,
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
        identifier: cprops.string,
    };
    if (cprops.record.id !== cprops.record.model.root.id) {
        // Only List View
        options.isAvailable = () => cprops.record.model.multiEdit && cprops.record.selected;
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
    if (cprops.record.id === cprops.record.model.root.id) {
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
