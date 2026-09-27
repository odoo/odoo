import { Plugin } from "@html_editor/plugin";

// TODO: In master adapt following code in xml
export class PasswordInputPlugin extends Plugin {
    static id = "password";
    resources = {
        force_not_editable_selector:
            "*:has(> input[type='password']:not([contenteditable='true']))",
    };
}
