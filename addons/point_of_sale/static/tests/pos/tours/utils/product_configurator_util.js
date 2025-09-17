export function pickRadio(name) {
    return [
        {
            content: `picking radio attribute with name ${name}`,
            trigger: `.modal .attribute-name-cell:contains('${name}') input`,
            run: "click",
        },
    ];
}
export function pickSelect(name) {
    return [
        {
            content: `picking select attribute with name ${name}`,
            trigger: `.modal .configurator_select:has(option:contains('${name}'))`,
<<<<<<< 6b08c4eeafd2913c385c63f8aba79738fd4743ce
            run: `select ${name}`,
||||||| 45fcd9716fe8cabd4db2ddbdf54caa8f69d5a013
            run: () => {
                const selects = queryAll`.modal .configurator_select`;
                for (const select of selects) {
                    const option = Array.from(select.options).find(
                        (opt) => opt.textContent.trim() === name
                    );
                    if (option) {
                        select.value = option.value;
                        // Manually trigger change event
                        select.dispatchEvent(new Event("change", { bubbles: true }));
                        return;
                    }
                }
                throw new Error(`Option "${name}" not found in any select`);
            },
=======
            run: ({ queryAll }) => {
                const selects = queryAll`.modal .configurator_select`;
                for (const select of selects) {
                    const option = Array.from(select.options).find(
                        (opt) => opt.textContent.trim() === name
                    );
                    if (option) {
                        select.value = option.value;
                        // Manually trigger change event
                        select.dispatchEvent(new Event("change", { bubbles: true }));
                        return;
                    }
                }
                throw new Error(`Option "${name}" not found in any select`);
            },
>>>>>>> c409575f1c1d2dd0d161657cb1bbadcba2df99af
        },
    ];
}
<<<<<<< 6b08c4eeafd2913c385c63f8aba79738fd4743ce
||||||| 45fcd9716fe8cabd4db2ddbdf54caa8f69d5a013

export function selectedSelect(name) {
    return [
        {
            content: `check selected value for select containing option "${name}"`,
            trigger: `.modal .configurator_select:has(option:contains(${name}))`,
            run: () => {
                const selects = queryAll`.modal .configurator_select:has(option:contains(${name}))`;
                for (const select of selects) {
                    const selected = select.options[select.selectedIndex];
                    if (selected?.textContent.trim() === name) {
                        return true;
                    }
                }
                throw new Error(`No select found with option "${name}" selected`);
            },
        },
    ];
}

=======

export function selectedSelect(name) {
    return [
        {
            content: `check selected value for select containing option "${name}"`,
            trigger: `.modal .configurator_select:has(option:contains(${name}))`,
            run: ({ queryAll }) => {
                const selects = queryAll`.modal .configurator_select:has(option:contains(${name}))`;
                for (const select of selects) {
                    const selected = select.options[select.selectedIndex];
                    if (selected?.textContent.trim() === name) {
                        return true;
                    }
                }
                throw new Error(`No select found with option "${name}" selected`);
            },
        },
    ];
}

>>>>>>> c409575f1c1d2dd0d161657cb1bbadcba2df99af
export function pickColor(name) {
    return [
        {
            content: `picking color attribute with name ${name}`,
            trigger: `.modal .configurator_color[data-color='${name}']`,
            run: "click",
        },
    ];
}
export function fillCustomAttribute(value) {
    return [
        {
            content: `filling custom attribute with value ${value}`,
            trigger: `.modal .custom_value`,
            run: `edit ${value}`,
        },
    ];
}

<<<<<<< 6b08c4eeafd2913c385c63f8aba79738fd4743ce
||||||| 45fcd9716fe8cabd4db2ddbdf54caa8f69d5a013
export function selectedCustomAttribute(value) {
    return [
        {
            content: `checking selected custom attribute with value "${value}"`,
            // trigger: `.modal .custom_value:contains('${value}')`,
            trigger: `.modal .custom_value`,
            run: () => {
                const inputs = queryAll(".modal .custom_value");
                for (const input of inputs) {
                    const actual = input.value?.trim();
                    if (actual === value) {
                        return true;
                    }
                }
                throw new Error(`No custom input found with value "${value}"`);
            },
        },
    ];
}

=======
export function selectedCustomAttribute(value) {
    return [
        {
            content: `checking selected custom attribute with value "${value}"`,
            // trigger: `.modal .custom_value:contains('${value}')`,
            trigger: `.modal .custom_value`,
            run: ({ queryAll }) => {
                const inputs = queryAll(".modal .custom_value");
                for (const input of inputs) {
                    const actual = input.value?.trim();
                    if (actual === value) {
                        return true;
                    }
                }
                throw new Error(`No custom input found with value "${value}"`);
            },
        },
    ];
}

>>>>>>> c409575f1c1d2dd0d161657cb1bbadcba2df99af
export function numberRadioOptions(number) {
    return [
        {
            trigger: `.attribute-name-cell`,
            run: () => {
                const radio_options = document.querySelectorAll(".attribute-name-cell").length;
                if (radio_options !== number) {
                    throw new Error(`Expected ${number} radio options, got ${radio_options}`);
                }
            },
        },
    ];
}

export function isOptionShown(option) {
    return [
        {
            content: `option ${option} is shown`,
            trigger: `.form-check-label:contains('${option}')`,
        },
    ];
}

export function isUnavailable(option) {
    return [
        {
            content: `option ${option} is unavailable`,
            trigger: `.modal .attribute span.text-muted:contains('${option}')`,
        },
    ];
}

export function isAddDisabled() {
    return [
        {
            content: "Add button is disabled",
            trigger: ".modal .btn-primary.disabled",
        },
    ];
}

export function isAddEnabled() {
    return [
        {
            content: "Add button is enabled",
            trigger: ".modal .btn-primary:not(.disabled)",
        },
    ];
}
