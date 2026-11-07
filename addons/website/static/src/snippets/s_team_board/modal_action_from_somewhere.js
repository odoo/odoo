import { registry } from "@web/core/registry";

registry.category("website.team_board_snippet.modal_actions").add("copy_email", {
    id: "copy_email",
    label: "Copy Email",
    loadingLabel: "Copying...",
    btnClass: "btn-outline-secondary",
    sequence: 20,
    action: async ({ notification }) => {
        await navigator.clipboard.writeText("placeholder@mail.mail");
        notification.add("Email copied to clipboard!", { type: "success" });
        return true;
    },
});
