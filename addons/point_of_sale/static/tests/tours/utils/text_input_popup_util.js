export function inputText(val) {
    return {
        content: `input text '${val}'`,
        trigger: `.modal:not(.o_inactive_modal) textarea`,
        in_modal: false,
        run: `edit ${val}`,
    };
}
