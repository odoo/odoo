import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class CustomersAvatarsOptionPlugin extends Plugin {
    static id = "customersAvatarOption";
    selector = ".s_customers_avatars";
    resources = {
        builder_options: [
            {
                template: "website.CustomersAvatarsOption",
                selector: this.selector,
                applyTo: ".s_customers_avatars_wrapper"
            },
        ],
        builder_actions: {
            customersAvatarsRoundness: {
                getValue: ({ editingElement }) => {
                    for (let x = 0; x <= 5; x++) {
                        if (editingElement.classList.contains(`rounded-${x}`)) return x;
                    }
                    return 0;
                },
                apply: ({ editingElement, value }) => {
                    for (let x = 0; x <= 5; x++) editingElement.classList.remove(`rounded-${x}`);
                    editingElement.classList.add(`rounded-${value}`);
                },
            },
        },
        so_content_addition_selector: [".s_customers_avatars"],
    };

    setup() {
        // Initialize avatar elements with default attributes
        this.editable.querySelectorAll(this.selector).forEach(element => {
            const defaults = [
                ['data-avatar-count', '3'],
                ['data-show-additional', 'false'],
                ['data-additional-count', '10']
            ];
            defaults.forEach(([attr, value]) => {
                if (!element.hasAttribute(attr)) element.setAttribute(attr, value);
            });
            this._updateAvatarDisplay(element);
        });

        // Set up mutation observer for dynamic updates
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                if (mutation.type === 'attributes') this._handleMutation(mutation);
            });
        });
        
        observer.observe(this.editable, {
            attributes: true,
            attributeFilter: ['data-avatar-count', 'data-show-additional', 'data-additional-count', 'style', 'class'],
            subtree: true
        });
    }

    _handleMutation(mutation) {
        const { target, attributeName } = mutation;
        
        if (target.matches(this.selector) && 
            ['data-avatar-count', 'data-show-additional', 'data-additional-count'].includes(attributeName)) {
            this._updateAvatarDisplay(target);
        }
        else if ((target.matches('.o_avatar') || target.matches(this.selector)) &&
                ['style', 'class'].includes(attributeName)) {
            const container = target.closest(this.selector) || target;
            if (container.dataset.showAdditional === 'true') {
                this._updateAvatarDisplay(container);
            }
        }
    }

    _updateAvatarDisplay(editingElement) {
        const wrapper = editingElement.querySelector('.s_customers_avatars_wrapper');
        if (!wrapper) return;

        const avatars = wrapper.querySelectorAll('.o_avatar');
        const avatarCount = parseInt(editingElement.dataset.avatarCount) || 3;
        const showAdditional = editingElement.dataset.showAdditional === 'true';
        const additionalCount = parseInt(editingElement.dataset.additionalCount) || 10;

        // Clean up existing overflow elements
        wrapper.querySelector('.o_avatar_count')?.remove();

        // Set avatar visibility
        avatars.forEach((avatar, index) => {
            avatar.style.display = index < avatarCount ? '' : 'none';
        });

        // Create overflow avatar if needed
        if (showAdditional) {
            const overflowAvatar = this._createOverflowAvatar(wrapper, additionalCount);
            if (avatars.length > 0) this._copyAvatarStyles(avatars[0], overflowAvatar);
        }
    }

    _createOverflowAvatar(wrapper, overflowCount) {
        const overflowAvatar = document.createElement('div');
        overflowAvatar.className = 'o_avatar_count';
        overflowAvatar.textContent = `+${overflowCount}`;
        wrapper.appendChild(overflowAvatar);
        return overflowAvatar;
    }

    _copyAvatarStyles(sourceAvatar, targetAvatar) {
        const sourceStyle = sourceAvatar.style;
        const computedStyle = getComputedStyle(sourceAvatar);
        const targetStyle = targetAvatar.style;
        
        // Copy border properties
        const borders = [
            ['borderWidth', 'medium', '0px'],
            ['borderStyle', 'none'],
            ['borderColor', 'currentcolor'],
            ['borderRadius', '0px']
        ];
        
        borders.forEach(([prop, ...invalid]) => {
            const value = sourceStyle[prop] || computedStyle[prop];
            if (value && !invalid.includes(value)) targetStyle[prop] = value;
        });
        
        // Copy roundness classes
        for (let i = 0; i <= 5; i++) {
            if (sourceAvatar.classList.contains(`rounded-${i}`)) {
                targetAvatar.className = targetAvatar.className.replace(/rounded-\d+/g, '');
                targetAvatar.classList.add(`rounded-${i}`);
                break;
            }
        }
    }
}
registry.category("website-plugins").add(CustomersAvatarsOptionPlugin.id, CustomersAvatarsOptionPlugin);
