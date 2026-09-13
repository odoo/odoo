import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { AddSnippetDialogSandboxed } from "./snippet_viewer/add_snippet_dialog";
import { registry } from "@web/core/registry";

export class MassMailingSnippetModel extends SnippetModel {
    getTechnicalUsage() {
        return "mass_mailing";
    }

    getAddSnippetDialogClass() {
        return AddSnippetDialogSandboxed;
    }
}

registry
    .category("html_builder.snippetsModel")
    .add("mass_mailing.email_designer_snippets", MassMailingSnippetModel);
