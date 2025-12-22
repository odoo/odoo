export function has(item, { run = () => {} } = {}) {
    return [
        {
            content: `selection popup has '${item}'`,
            trigger: `.selection-item:contains("${item}")`,
            run,
        },
    ];
}
