import { registry } from "@web/core/registry";

function createVolume(name, width, depth, height) {
    return [
        {
            trigger: `button:contains(new)`,
            run: "click",
        },
        {
            trigger: "tr:eq(1) td[name=name] input",
            run: `edit ${name}`,
        },
        {
            trigger: "tr:eq(1) td[name=width] input",
            run: `edit ${width}`,
        },
        {
            trigger: "tr:eq(1) td[name=height] input",
            run: `edit ${height}`,
        },
        {
            trigger: "tr:eq(1) td[name=depth] input",
            run: `edit ${depth}`,
        },
        {
            trigger: "button:contains(save)",
            run: "click",
        },
    ];
}

registry.category("web_tour.tours").add("tour_create_volumes", {
    steps: () => [
        {
            trigger: `[data-menu-xmlid="smartclass.menu_root"]`,
            run: "click",
        },
        ...createVolume("Volume 1", 2.56, 3.78, 4.23),
        ...createVolume("Volume 2", 1.45, 0.3444, 4),
        ...createVolume("Volume 3", 1, 2, 3),
        ...createVolume("Volume 4", 1, 1, 60),
        ...createVolume("Volume 5", 70, 80, 90),
    ],
});
