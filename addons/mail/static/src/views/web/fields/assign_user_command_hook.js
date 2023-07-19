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
            component.props.record.data[component.props.name].replaceWith([
                ...getCurrentIds(),
                record[0],
            ]);
        }
    };

    const remove = async (record) => {
        if (type === "many2one") {
            component.props.record.update({ [component.props.name]: [] });
        } else if (type === "many2many") {
            component.props.record.data[component.props.name].replaceWith(
                getCurrentIds().filter((id) => id !== record[0])
            );
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
        const searchResult = await orm.call(component.relation, "name_search", [], {
            name: value,
            args: domain,
            operator: "ilike",
            limit: 80,
            context,
        });
        return searchResult.map((record) => ({
            name: record[1],
            action: add.bind(null, record),
        }));
    };

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
            category: "smart_action",
            hotkey: "alt+i",
            global: true,
        }
    );

    useCommand(
        _t("Assign/Unassign to me"),
        () => {
            const record = [user.userId, user.name];
            if (getCurrentIds().includes(user.userId)) {
                remove(record);
            } else {
                add(record);
            }
        },
        {
            category: "smart_action",
            hotkey: "alt+shift+i",
            global: true,
        }
    );
}
