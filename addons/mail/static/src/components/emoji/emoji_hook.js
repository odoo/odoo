/** @odoo-module */

import { useEffect } from "@web/core/utils/hooks";
const { useComponent } = owl.hooks;

export function useEmojis() {
    const component = useComponent();
    useEffect(
        () => { 
            twemoji.parse(component.el, {
                folder: 'svg',
                ext: '.svg'
            }); 
        },
    );
}

export function useEmojisOnDiscussComponent(element) {
    twemoji.parse(element, {
        folder: 'svg',
        ext: '.svg'
    }); 
}
