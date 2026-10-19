import { _t } from "@web/core/l10n/translation";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { AvatarUserFormViewDialog } from "@mail/views/web/view_dialog/avatar_user_form_view_dialog";

export class Many2XAvatarUserAutocomplete extends Many2XAutocomplete {
    get actionSuggestions() {
        return [
            {
                enabled: () => this.activeActions.create,
                build: (request) => {
                    const label = request
                        ? _t(`Invite "%s"`, request)
                        : _t("Invite teammates via email");
                    return {
                        cssClass:
                            "o_m2o_dropdown_option o_m2o_dropdown_option_create text-indent-3",
                        label: label,
                        data: { slotName: "inviteTeammates", label: label },
                        onSelect: () => this.slowCreate(request),
                    };
                },
            },
            {
                enabled: this.addSearchMoreSuggestion.bind(this),
                build: this.buildSearchMoreSuggestion.bind(this),
            },
        ];
    }

    get createDialog() {
        return AvatarUserFormViewDialog;
    }

    get createDialogSize() {
        return "md";
    }

    slowCreate(request) {
        return this.openMany2X({
            context: this.getCreationContext(request),
            nextRecordsContext: this.props.context,
            title: _t("Invite teammates"),
        });
    }
}
