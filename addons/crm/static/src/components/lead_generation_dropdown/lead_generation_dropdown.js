import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ErrorDialog } from "@web/core/errors/error_dialogs";

export const MODULE_STATUS = {
    NOT_INSTALLED: "NOT_INSTALLED",
    INSTALLING: "INSTALLING",
    FAILED_TO_INSTALL: "FAILED_TO_INSTALL",
    INSTALLED: "INSTALLED",
};

export class LeadGenerationDropdown extends Component {
    static template = "crm.lead_generation_dropdown";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        this.orm = useService("orm");
        this.dialogs = useService("dialog");
        this.action = useService("action");
        this.newContentText = {
            FAILED_TO_INSTALL: _t('Failed to install "%(module_name)s"'),
            INSTALLING: _t('Installing "%(module_name)s"'),
            NOT_INSTALLED: _t('Do you want to install the "%(module_name)s" App?'),
        };

        this.state = useState({
            dropdownContentElements: [
                {
                    description: _t("Search in our directory of 300.000+ companies"),
                    hasAccess: user.isAdmin,
                    icon: "/crm/static/src/img/lead_sourcing.png",
                    sequence: 10,
                    moduleName: "crm_iap_mine",
                    moduleXmlId: "base.module_crm_iap_mine",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    title: _t("Lead Sourcing"),
                },
                {
                    description: _t("Turn visitors into leads"),
                    hasAccess: user.isAdmin,
                    icon: "/crm/static/src/img/website.png",
                    sequence: 20,
                    moduleName: "website",
                    moduleXmlId: "base.module_website",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    title: _t("Create a landing page"),
                },
                {
                    description: _t("Send an email and get leads from replies"),
                    hasAccess: user.isAdmin,
                    icon: "/crm/static/src/img/mail.png",
                    sequence: 30,
                    moduleName: "mass_mailing",
                    moduleXmlId: "base.module_mass_mailing",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    title: _t("Email Marketing"),
                },
                {
                    description: _t("Create leads on specific answers"),
                    hasAccess: user.isAdmin,
                    icon: "/crm/static/src/img/survey.png",
                    sequence: 40,
                    moduleName: "survey",
                    moduleXmlId: "base.module_survey",
                    status: MODULE_STATUS.NOT_INSTALLED,
                    title: _t("Send a Survey"),
                },
                {
                    description: _t("Generate leads from any email you get"),
                    hasAccess: true,
                    icon: "/crm/static/src/img/mail_plugins.png",
                    sequence: 50,
                    moduleName: "Mail Plugins",
                    moduleXmlId: "not_a_module",
                    onClick: () => this.redirectToMailDocs(),
                    status: MODULE_STATUS.INSTALLED,
                    title: _t("Mail plugins"),
                },
            ],
        });
        this.dropdown = useDropdownState();
        useHotkey("escape", () => this.dropdown.close(), {
            isAvailable: () => this.dropdown.isOpen,
        });
    }

    swapDescription(element) {
        if (element.status !== MODULE_STATUS.NOT_INSTALLED && element.hasAccess) {
            return;
        }
        if (!element.swappedDescription) {
            element.swappedDescription = true;
        }
    }

    resetDescription(element) {
        element.swappedDescription = false;
    }

    async toggleDropdown() {
        for (const dropdownContentElement in this.state.dropdownContentElements) {
            this.resetDescription(this.state.dropdownContentElements[dropdownContentElement]);
        }
        if (this.dropdownWasAlreadyOpened) {
            this.dropdown.isOpen = !this.dropdown.isOpen;
            return;
        }
        this.dropdownWasAlreadyOpened = true;

        const proms = [];
        proms.push(
            (async () => {
                const moduleNames = this.state.dropdownContentElements.map(
                    ({ moduleName }) => moduleName
                );
                this.modulesInfo = {};
                for (const record of await this.orm
                    .cache()
                    .searchRead(
                        "ir.module.module",
                        [["name", "in", moduleNames]],
                        ["id", "name", "shortdesc"]
                    )) {
                    this.modulesInfo[record.name] = { id: record.id, name: record.shortdesc };
                }
            })()
        );

        proms.push(
            (async () => {
                const modelsToCheck = [];
                const elementsToUpdate = {};
                for (const element of this.state.dropdownContentElements) {
                    if (element.model) {
                        modelsToCheck.push(element.model);
                        elementsToUpdate[element.model] = element;
                    }
                }
                if (!modelsToCheck.length) {
                    return;
                }
                const accesses = await Promise.all(
                    modelsToCheck.map(async (model) => [
                        model,
                        await user.checkAccessRight(model, "create"),
                    ])
                );
                for (const [model, access] of accesses) {
                    elementsToUpdate[model].hasAccess = access;
                }
            })()
        );

        await Promise.all(proms);
        this.dropdown.open();
    }

    get sortedDropdownContentElements() {
        return this.state.dropdownContentElements
            .filter(({ status, hasAccess }) => status !== MODULE_STATUS.NOT_INSTALLED && hasAccess)
            .toSorted((a, b) => a.sequence - b.sequence)
            .concat(
                this.state.dropdownContentElements
                    .filter(
                        ({ status, hasAccess }) =>
                            status === MODULE_STATUS.NOT_INSTALLED || !hasAccess
                    )
                    .toSorted((a, b) => a.sequence - b.sequence)
            );
    }

    onClickAction(element) {
        if (!element.hasAccess) {
            return;
        }

        if (element.status === MODULE_STATUS.INSTALLED) {
            return element.onClick();
        }

        if (!user.isAdmin) {
            return;
        }

        const { id, name } = this.modulesInfo[element.moduleName];
        const dialogProps = {
            title: element.title,
            body: sprintf(this.newContentText["NOT_INSTALLED"], { module_name: name }),
            confirm: async () => {
                this.setElementStatus(element, name, MODULE_STATUS.INSTALLING);
                try {
                    await this.orm.silent.call("ir.module.module", "button_immediate_install", [
                        id,
                    ]);
                    location.reload();
                } catch (error) {
                    this.setElementStatus(element, name, MODULE_STATUS.FAILED_TO_INSTALL);
                    this.dialogs.add(ErrorDialog, { message: error });
                    console.error(error);
                }
            },
            cancel: () => {},
            confirmLabel: "Install",
            cancelLabel: "Cancel",
        };
        this.dialogs.add(ConfirmationDialog, dialogProps);
    }

    setElementStatus(element, name, status) {
        this.state.dropdownContentElements.forEach((el) => {
            if (el.moduleXmlId === element.moduleXmlId) {
                el.status = status;
                el.title = sprintf(this.newContentText[status], { module_name: name });
            }
        });
    }

    /*** Button Actions ***/
    redirectToMailDocs() {
        this.action.doAction({
            type: "ir.actions.act_url",
            url: "https://www.odoo.com/documentation/19.0/applications/general/integrations/mail_plugins.html",
            target: "new",
        });
    }
}
